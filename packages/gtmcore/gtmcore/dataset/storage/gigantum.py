import asyncio
import aiohttp
import aiofiles
import copy
import snappy
import tempfile
import requests
import math
import time

from gtmcore.dataset import Dataset
from gtmcore.dataset.storage.backend import ManagedStorageBackend
from typing import Optional, List, Dict, Callable, Tuple, NamedTuple
import os

from gtmcore.dataset.io import PushResult, PushObject, PullResult, PullObject
from gtmcore.logging import LMLogger
from gtmcore.dataset.manifest.eventloop import get_event_loop

logger = LMLogger.get_logger()


# Namedtuples to track parts in a multipart upload
MultipartPart = NamedTuple("MultipartUploadPart", [('part_number', int), ('start_byte', int), ('end_byte', int)])
MultipartPartCompleted = NamedTuple("MultipartUploadPart", [('part_number', int), ('etag', str)])


class PresignedS3Upload(object):
    def __init__(self, object_service_root: str, object_service_headers: dict,
                 multipart_chunk_size: int, upload_chunk_size: int,
                 object_details: PushObject) -> None:
        self.service_root = object_service_root
        self.object_service_headers = object_service_headers
        self.upload_chunk_size = upload_chunk_size

        self.object_details = object_details
        self.skip_object = False
        self._compressed_object_path: Optional[str] = None
        self._compressed_object_size: Optional[int] = None

        self.presigned_s3_url = ""
        self.s3_headers: Dict = dict()

        # Multi-part upload support
        self.multipart_chunk_size = multipart_chunk_size
        self.multipart_upload_id = None
        self._multipart_parts: List[MultipartPart] = list()
        self._multipart_completed_parts: List[MultipartPartCompleted] = list()

    @property
    def is_presigned(self) -> bool:
        """Property to check if this upload request has successfully been presigned

        Returns:
            bool
        """
        return self.presigned_s3_url != ""

    @property
    def compressed_object_size(self) -> int:
        """Property to get the size of the compressed object

        Returns:
            bool
        """
        if not self._compressed_object_size:
            self._compressed_object_size = os.path.getsize(self.compressed_object_path)
        return self._compressed_object_size

    @property
    def is_multipart(self) -> bool:
        """Property to check if this object is over the multi-part threshold and should be sent via multi-part upload
        process

        Returns:
            bool
        """
        return self.compressed_object_size >= self.multipart_chunk_size

    @property
    def current_part(self) -> Optional[MultipartPart]:
        """Property to get the current part to be processed and uploaded

        Returns:
            MultipartPart
        """
        if self._multipart_parts:
            return self._multipart_parts[0]
        else:
            return None

    @property
    def object_id(self) -> str:
        """Property to get the object ID related to this instance

        Returns:

        """
        # Get the object id from the object path
        _, obj_id = self.object_details.object_path.rsplit('/', 1)
        return obj_id

    @property
    def compressed_object_path(self) -> str:
        """Property to get the compressed object path, and if not set, compress the object

        Returns:
            str
        """
        if not self._compressed_object_path:
            self._compressed_object_path = os.path.join('/tmp', self.object_id)
            with open(self.object_details.object_path, "rb") as src_file:
                with open(self._compressed_object_path, "wb") as compressed_file:
                    snappy.stream_compress(src_file, compressed_file)

        return self._compressed_object_path

    def remove_compressed_file(self) -> None:
        try:
            os.remove(self.compressed_object_path)
        except FileNotFoundError:
            # Temp file never got created, just move on
            pass

    def mark_current_part_complete(self, etag: str) -> None:
        """Method to mark the current part as successfully uploaded

        Returns:
            None
        """
        current_part: MultipartPart = self._multipart_parts.pop(0)
        self._multipart_completed_parts.append(MultipartPartCompleted(current_part.part_number, etag))
        self.presigned_s3_url = ""

    def get_completed_parts(self) -> List[dict]:
        """Method to get the etag and part number data required by S3 to complete the multipart upload

        Returns:
            List
        """
        return [dict(ETag=p.etag, PartNumber=p.part_number) for p in self._multipart_completed_parts]

    def set_s3_headers(self, encryption_key_id: str) -> None:
        """Method to set the header property for S3

        Args:
            encryption_key_id: The encryption key id returned from the object service. This is required so the request
                               made to s3 is consistent with what was signed

        Returns:
            None
        """
        if self.is_multipart:
            self.s3_headers = dict()
        else:
            self.s3_headers = {'x-amz-server-side-encryption': 'aws:kms',
                               'x-amz-server-side-encryption-aws-kms-key-id': encryption_key_id}

    async def get_presigned_s3_url(self, session: aiohttp.ClientSession) -> None:
        """Method to make a request to the object service and pre-sign an S3 PUT

        Args:
            session: The current aiohttp session

        Returns:
            None
        """
        if self.is_multipart:
            if not self.current_part:
                raise ValueError("No parts remain to get presigned URL.")

            part_num = self.current_part.part_number
            url = f"{self.service_root}/{self.object_id}/multipart/{self.multipart_upload_id}/part/{part_num}"
        else:
            url = f"{self.service_root}/{self.object_id}"

        try_count = 0
        error_status = None
        error_msg = None
        while try_count < 3:
            async with session.put(url, headers=self.object_service_headers) as response:
                if response.status == 200:
                    # Successfully signed the request
                    response_data = await response.json()
                    self.presigned_s3_url = response_data.get("presigned_url")
                    self.set_s3_headers(response_data.get("key_id"))
                    return
                elif response.status == 403:
                    # Forbidden indicates Object already exists,
                    # don't need to re-push since we deduplicate so mark it skip
                    self.skip_object = True
                    return
                else:
                    # Something when wrong while trying to pre-sign the URL.
                    error_msg = await response.json()
                    error_status = response.status
                    await asyncio.sleep(try_count ** 2)
                    try_count += 1

        raise IOError(f"Failed to get pre-signed URL for PUT at "
                      f"{self.object_details.dataset_path}:{self.object_id}."
                      f" Status: {error_status}. Response: {error_msg}")

    async def _file_loader(self, filename: str, progress_update_fn: Callable):
        """Method to provide non-blocking chunked reads of files, useful if large.

        Args:
            filename: absolute path to the file to upload
            progress_update_fn: A callable with arg "completed_bytes" (int) indicating how many bytes have been
                                uploaded in since last called
        """
        async with aiofiles.open(filename, 'rb') as f:
            if self.is_multipart:
                if not self.current_part:
                    raise ValueError("No parts remain to get presigned URL.")

                # if multipart, seek to the proper spot in the file
                await f.seek(self.current_part.start_byte)

            read_bytes = 0
            chunk = await f.read(self.upload_chunk_size)
            while chunk:
                progress_update_fn(completed_bytes=len(chunk))
                read_bytes += len(chunk)
                yield chunk

                if self.is_multipart:
                    if not self.current_part:
                        raise ValueError("No parts remain to get presigned URL.")
                    if self.current_part.start_byte + read_bytes >= self.current_part.end_byte:
                        # You're done reading for this part
                        break

                # Keep reading and streaming chunks for this part
                chunk = await f.read(self.upload_chunk_size)

    async def prepare_multipart_upload(self, session: aiohttp.ClientSession) -> None:
        """Method to prepare a multipart upload by computing parts and getting an upload ID

        Args:
            session: The current aiohttp session

        Returns:
            None
        """
        num_parts = math.floor(float(self.compressed_object_size) / float(self.multipart_chunk_size))
        start_byte = 0
        for part in range(1, num_parts + 1):
            self._multipart_parts.append(MultipartPart(part_number=part, start_byte=start_byte,
                                                       end_byte=start_byte + self.multipart_chunk_size))
            start_byte = start_byte + self.multipart_chunk_size

        remainder = self.compressed_object_size - (self.multipart_chunk_size * num_parts)
        if remainder:
            # If not perfectly divisible by the chunk size, add one more partial part
            self._multipart_parts.append(MultipartPart(part_number=len(self._multipart_parts) + 1,
                                                       start_byte=start_byte,
                                                       end_byte=start_byte + remainder))

        logger.info(self._multipart_parts)

        # Make a call and create a multipart upload
        try_count = 0
        error_status = None
        error_msg = None
        while try_count < 3:
            async with session.post(f"{self.service_root}/{self.object_id}/multipart",
                                    headers=self.object_service_headers) as response:
                if response.status == 200:
                    data = await response.json()
                    self.multipart_upload_id = data['upload_id']
                    logger.info(f"Created multipart upload for {self.object_details.dataset_path} at"
                                f" {self.object_details.revision[0:8]}, with {len(self._multipart_parts)} "
                                f"parts: {self.multipart_upload_id}")
                    return
                elif response.status == 403:
                    # Forbidden indicates Object already exists,
                    # don't need to re-push since we deduplicate so mark it skip
                    self.skip_object = True
                    return
                else:
                    # An error occurred
                    logger.warning(f"Failed to push {self.object_details.dataset_path}. Try {try_count + 1} of 3")
                    error_msg = await response.text()
                    error_status = response.status
                    await asyncio.sleep(try_count ** 2)
                    try_count += 1

        raise IOError(f"Failed to push {self.object_details.dataset_path} to storage backend."
                      f" Status: {error_status}. Response: {error_msg}")

    async def complete_multipart_upload(self, session: aiohttp.ClientSession) -> None:
        """Method to prepare a multipart upload by computing parts and getting an upload ID

        Args:
            session: The current aiohttp session

        Returns:
            None
        """
        if self.current_part:
            raise ValueError("All parts should be complete before calling `complete_multipart_upload()`")

        try_count = 0
        error_status = None
        error_msg = None
        while try_count < 3:
            async with session.post(f"{self.service_root}/{self.object_id}/multipart/{self.multipart_upload_id}",
                                    json=self.get_completed_parts(),
                                    headers=self.object_service_headers) as response:
                if response.status != 200:
                    # An error occurred
                    logger.warning(f"Failed to complete {self.object_details.dataset_path}. Try {try_count + 1} of 3")
                    error_msg = await response.text()
                    error_status = response.status
                    await asyncio.sleep(try_count ** 2)
                    try_count += 1
                else:
                    # All good.
                    logger.info(f"Completed multipart upload {self.multipart_upload_id} for "
                                f"{self.object_details.dataset_path} at {self.object_details.revision[0:8]}.")
                    self.remove_compressed_file()
                    return

        raise IOError(f"Failed to complete multipart upload for {self.object_details.dataset_path}."
                      f" Status: {error_status}. Response: {error_msg}")

    async def abort_multipart_upload(self, session: aiohttp.ClientSession) -> None:
        """Method to abort a multipart upload

        Args:
            session: The current aiohttp session

        Returns:
            None
        """
        if not self.multipart_upload_id:
            raise ValueError("An upload id is required to abort a multipart upload")

        try_count = 0
        error_status = None
        error_msg = None
        while try_count < 3:
            async with session.delete(f"{self.service_root}/{self.object_id}/multipart/{self.multipart_upload_id}",
                                      headers=self.object_service_headers) as response:
                if response.status != 204:
                    # An error occurred
                    logger.warning(f"Failed to abort {self.object_details.dataset_path}. Try {try_count + 1} of 3")
                    error_msg = await response.text()
                    error_status = response.status
                    await asyncio.sleep(try_count ** 2)
                    try_count += 1
                else:
                    # All good.
                    logger.info(f"Aborted multipart upload {self.multipart_upload_id} for "
                                f"{self.object_details.dataset_path} at {self.object_details.revision[0:8]}.")
                    return

        raise IOError(f"Failed to abort multipart upload for {self.object_details.dataset_path}."
                      f" Status: {error_status}. Response: {error_msg}")

    async def put_object(self, session: aiohttp.ClientSession, progress_update_fn: Callable) -> str:
        """Method to put the object in S3 after the pre-signed URL has been obtained

        Args:
            session: The current aiohttp session
            progress_update_fn: A callable with arg "completed_bytes" (int) indicating how many bytes have been
                                uploaded in since last called

        Returns:
            None
        """
        # Set the Content-Length of the PUT explicitly since it won't happen automatically due to streaming IO
        headers = copy.deepcopy(self.s3_headers)

        # compress object before upload
        if self.is_multipart:
            if not self.current_part:
                raise ValueError(f"Failed to put_object part. No parts remain for {self.object_id}")
            headers['Content-Length'] = str(self.current_part.end_byte - self.current_part.start_byte)
        else:
            headers['Content-Length'] = str(self.compressed_object_size)

        # Stream the file up to S3
        try_count = 0
        error_msg = None
        error_status = None
        while try_count < 3:
            async with session.put(self.presigned_s3_url, headers=headers,
                                   data=self._file_loader(filename=self.compressed_object_path,
                                                          progress_update_fn=progress_update_fn)) as response:
                if response.status != 200:
                    # An error occurred, retry
                    error_msg = await response.text()
                    error_status = response.status
                    await asyncio.sleep(try_count ** 2)
                    try_count += 1
                else:
                    return response.headers['Etag']

        raise IOError(f"Failed to push {self.object_details.dataset_path} to storage backend."
                      f" Status: {error_status}. Response: {error_msg}")


class PresignedS3Download(object):
    def __init__(self, object_service_root: str, object_service_headers: dict, download_chunk_size: int,
                 object_details: PullObject) -> None:
        self.service_root = object_service_root
        self.object_service_headers = object_service_headers
        self.download_chunk_size = download_chunk_size

        self.object_details = object_details

        self.presigned_s3_url = ""

    @property
    def is_presigned(self) -> bool:
        """Method to check if this upload request has successfully been presigned

        Returns:
            bool
        """
        return self.presigned_s3_url != ""

    async def get_presigned_s3_url(self, session: aiohttp.ClientSession) -> None:
        """Method to make a request to the object service and pre-sign an S3 GET

        Args:
            session: The current aiohttp session

        Returns:
            None
        """
        # Get the object id from the object path
        _, obj_id = self.object_details.object_path.rsplit('/', 1)

        async with session.get(f"{self.service_root}/{obj_id}", headers=self.object_service_headers) as response:
            if response.status == 200:
                # Successfully signed the request
                response_data = await response.json()
                self.presigned_s3_url = response_data.get("presigned_url")
            else:
                # Something when wrong while trying to pre-sign the URL.
                body = await response.json()
                raise IOError(f"Failed to get pre-signed URL for GET at {self.object_details.dataset_path}:{obj_id}."
                              f" Status: {response.status}. Response: {body}")

    async def get_object(self, session: aiohttp.ClientSession, progress_update_fn: Callable) -> None:
        """Method to get the object from S3 after the pre-signed URL has been obtained

        Args:
            session: The current aiohttp session
            progress_update_fn: A callable with arg "completed_bytes" (int) indicating how many bytes have been
                                downloaded in since last called

        Returns:
            None
        """
        try:
            decompressor = snappy.StreamDecompressor()
            async with session.get(self.presigned_s3_url) as response:
                if response.status != 200:
                    # An error occurred
                    body = await response.text()
                    raise IOError(f"Failed to get {self.object_details.dataset_path} to storage backend."
                                  f" Status: {response.status}. Response: {body}")

                async with aiofiles.open(self.object_details.object_path, 'wb') as fd:
                    while True:
                        chunk = await response.content.read(self.download_chunk_size)
                        if not chunk:
                            fd.write(decompressor.flush())
                            break

                        decompressed_chunk = decompressor.decompress(chunk)
                        await fd.write(decompressed_chunk)
                        progress_update_fn(completed_bytes=len(decompressed_chunk))
        except Exception as err:
            logger.exception(err)
            raise IOError(f"Failed to get {self.object_details.dataset_path} from storage backend. {err}")


class GigantumObjectStore(ManagedStorageBackend):

    def __init__(self) -> None:
        # Additional attributes to track processed requests
        self.successful_requests: List = list()
        self.failed_requests: List = list()

        super().__init__()

    def _backend_metadata(self) -> dict:
        """Method to specify Storage Backend metadata for each implementation. This is used to render the UI

        Simply implement this method in a child class. Note, 'icon' should be the name of the icon file saved in the
        thumbnails directory. It should be a 128x128 px PNG image.

        Returns:
            dict
        """
        return {"storage_type": "gigantum_object_v1",
                "name": "Gigantum Cloud",
                "description": "Dataset storage provided by your Gigantum account supporting files up to 5GB in size",
                "tags": ["gigantum"],
                "icon": "gigantum_object_storage.png",
                "url": "https://docs.gigantum.com",
                "readme": """Gigantum Cloud Datasets are backed by a scalable object storage service that is linked to
your Gigantum account and credentials. It provides efficient storage at the file level and works seamlessly with the
Client.

This dataset type is fully managed. That means as you modify data, each version will be tracked independently. Syncing
to Gigantum Cloud will count towards your storage quota and include all versions of files.
"""}

    @property
    def client_should_dedup_on_push(self) -> bool:
        return True

    def _required_configuration(self) -> List[Dict[str, str]]:
        """A private method to return a list of keys that must be set for a backend to be fully configured

        The format is a dict of keys and descriptions. E.g.

        {
          "server": "The host name for the remote server",
          "username": "The current logged in username"

        }

        There are 3 keys that are always automatically populated:
           - username: the gigantum username for the logged in user
           - gigantum_bearer_token: the gigantum bearer token for the current session
           - gigantum_id_token: the gigantum id token for the current session

        Returns:

        """
        # No additional config required beyond defaults
        return list()

    def confirm_configuration(self, dataset) -> Optional[str]:
        """Method to verify a configuration and optionally allow the user to confirm before proceeding

        Should return the desired confirmation message if there is one. If no confirmation is required/possible,
        return None

        """
        return None

    @staticmethod
    def _object_service_endpoint(dataset: Dataset) -> str:
        """

        Args:
            dataset:

        Returns:

        """
        remote_config = dataset.client_config.get_remote_configuration()
        obj_service = None
        if remote_config:
            obj_service = remote_config.get('object_service')

        if not obj_service:
            raise ValueError('Object Service endpoint not configured.')

        return f"https://{obj_service}"

    def _object_service_headers(self) -> dict:
        """Method to generate the request headers, including authorization information

        Returns:

        """
        return {'Authorization': f"Bearer {self.configuration.get('gigantum_bearer_token')}",
                'Identity': self.configuration.get("gigantum_id_token"),
                'Content-Type': 'application/json',
                'Accept': 'application/json'}

    def prepare_push(self, dataset, objects: List[PushObject]) -> None:
        """Gigantum Object Service only requires that the user's tokens have been set

        Args:
            dataset: The current dataset instance
            objects: A list of PushObjects to be pushed

        Returns:
            None
        """
        if 'username' not in self.configuration.keys():
            raise ValueError("Username must be set to push objects to Gigantum Cloud")

        if 'gigantum_bearer_token' not in self.configuration.keys():
            raise ValueError("User must have valid session to push objects to Gigantum Cloud")

        if 'gigantum_id_token' not in self.configuration.keys():
            raise ValueError("User must have valid session to push objects to Gigantum Cloud")

        # Pre-check auth so it gets cached and speeds up future requests
        url = f"{self._object_service_endpoint(dataset)}/{dataset.namespace}/{dataset.name}"
        response = requests.head(url, headers=self._object_service_headers(), timeout=60)
        if response.status_code == 200:
            access_level = response.headers.get('x-access-level')
            if access_level is not None and access_level != 'r':
                return

        # If you get here, doesn't exist, no access, or read-only
        raise IOError("Failed to push files to Gigantum Cloud. You either have read-only permissions or "
                      "the Dataset does not exist.")

    def finalize_push(self, dataset) -> None:
        pass

    def prepare_pull(self, dataset, objects: List[PullObject]) -> None:
        """Gigantum Object Service only requires that the user's tokens have been set

        Args:
            dataset: The current dataset instance
            objects: A list of PushObjects to be pulled

        Returns:
            None
        """
        if 'username' not in self.configuration.keys():
            raise ValueError("Username must be set to push objects to Gigantum Cloud")

        if 'gigantum_bearer_token' not in self.configuration.keys():
            raise ValueError("User must have valid session to push objects to Gigantum Cloud")

        if 'gigantum_id_token' not in self.configuration.keys():
            raise ValueError("User must have valid session to push objects to Gigantum Cloud")

        # Pre-check auth so it gets cached and speeds up future requests
        url = f"{self._object_service_endpoint(dataset)}/{dataset.namespace}/{dataset.name}"
        response = requests.head(url, headers=self._object_service_headers(), timeout=60)
        if response.status_code != 200:
            raise IOError("Failed to pull files from Gigantum Cloud. You either do not have access or "
                          "the Dataset does not exist.")

    def finalize_pull(self, dataset) -> None:
        pass

    async def _process_standard_upload(self, queue: asyncio.LifoQueue, session: aiohttp.ClientSession,
                                       presigned_request: PresignedS3Upload, progress_update_fn: Callable) -> None:
        """Method to handle the standard single request upload workflow.

        If a presigned url has not been generated, get it. if it has, put the file contents.

        Args:
            queue: The current work queue
            session: The current aiohttp session
            presigned_request: the current PresignedS3Upload object to process
            progress_update_fn: A callable with arg "completed_bytes" (int) indicating how many bytes have been
                                uploaded in since last called


        Returns:
            None
        """
        if not presigned_request.is_presigned:
            # Fetch the signed URL
            await presigned_request.get_presigned_s3_url(session)
            queue.put_nowait(presigned_request)
        else:
            # Process S3 Upload
            try:
                await presigned_request.put_object(session, progress_update_fn)
                self.successful_requests.append(presigned_request)
                presigned_request.remove_compressed_file()
            except Exception:
                presigned_request.remove_compressed_file()
                raise

    async def _process_multipart_upload(self, queue: asyncio.LifoQueue, session: aiohttp.ClientSession,
                                        presigned_request: PresignedS3Upload, progress_update_fn: Callable) -> None:
        """Method to handle the complex multipart upload workflow.

        1. Create a multipart upload and get the ID
        2. Upload all parts
        3. Complete the part and mark the PresignedS3Upload object as successful

        Args:
            queue: The current work queue
            session: The current aiohttp session
            presigned_request: the current PresignedS3Upload object to process
            progress_update_fn: A callable with arg "completed_bytes" (int) indicating how many bytes have been
                                uploaded in since last called


        Returns:
            None
        """
        if not presigned_request.multipart_upload_id:
            # Create a multipart upload and create parts
            await presigned_request.prepare_multipart_upload(session)
            # Requeue for more processing
            queue.put_nowait(presigned_request)
        else:
            try:
                if presigned_request.current_part:
                    if not presigned_request.is_presigned:
                        # Fetch the signed URL
                        await presigned_request.get_presigned_s3_url(session)
                        queue.put_nowait(presigned_request)
                    else:
                        # Process S3 Upload, mark the part as done, and requeue it
                        etag = await presigned_request.put_object(session, progress_update_fn)
                        presigned_request.mark_current_part_complete(etag)
                        queue.put_nowait(presigned_request)
                else:
                    # If you get here, you are done and should complete the upload
                    await presigned_request.complete_multipart_upload(session)
                    self.successful_requests.append(presigned_request)
            except Exception:
                presigned_request.remove_compressed_file()
                raise

    async def _push_object_consumer(self, queue: asyncio.LifoQueue, session: aiohttp.ClientSession,
                                    progress_update_fn: Callable) -> None:
        """Async Queue consumer worker for pushing objects to the object service/s3

        Args:
            queue: The current work queue
            session: The current aiohttp session
            progress_update_fn: A callable with arg "completed_bytes" (int) indicating how many bytes have been
                                uploaded in since last called

        Returns:
            None
        """
        while True:
            presigned_request: PresignedS3Upload = await queue.get()

            try:
                if presigned_request.skip_object is False:
                    if presigned_request.is_multipart:
                        # Run multipart upload workflow
                        await self._process_multipart_upload(queue, session, presigned_request, progress_update_fn)
                    else:
                        # Run standard, single-request workflow
                        await self._process_standard_upload(queue, session, presigned_request, progress_update_fn)
                else:
                    # Object skipped because it already exists in the backend (object level de-duplicating)
                    logger.info(f"Skipping duplicate download {presigned_request.object_details.dataset_path}")
                    progress_update_fn(os.path.getsize(presigned_request.object_details.object_path))
                    self.successful_requests.append(presigned_request)

            except Exception as err:
                logger.exception(err)
                self.failed_requests.append(presigned_request)
                if presigned_request.is_multipart and presigned_request.multipart_upload_id is not None:
                    # Make best effort to abort a multipart upload if needed
                    try:
                        await presigned_request.abort_multipart_upload(session)
                    except Exception as err:
                        logger.error(f"An error occured while trying to abort multipart upload "
                                     f"{presigned_request.multipart_upload_id} for {presigned_request.object_id}")
                        logger.exception(err)

            # Notify the queue that the item has been processed
            queue.task_done()

    @staticmethod
    async def _push_object_producer(queue: asyncio.LifoQueue, object_service_root: str, object_service_headers: dict,
                                    multipart_chunk_size: int, upload_chunk_size: int,
                                    objects: List[PushObject]) -> None:
        """Async method to populate the queue with upload requests

        Args:
            queue: The current work queue
            object_service_root: The root URL to use for all objects, including the namespace and dataset name
            object_service_headers: The headers to use when requesting signed urls, including auth info
            multipart_chunk_size: Size in bytes for break a file apart for multi-part uploading
            upload_chunk_size: Size in bytes for streaming IO chunks
            objects: A list of PushObjects to push

        Returns:
            None
        """
        for obj in objects:
            presigned_request = PresignedS3Upload(object_service_root,
                                                  object_service_headers,
                                                  multipart_chunk_size,
                                                  upload_chunk_size,
                                                  obj)
            await queue.put(presigned_request)

    async def _run_push_pipeline(self, object_service_root: str, object_service_headers: dict,
                                 objects: List[PushObject], progress_update_fn: Callable,
                                 multipart_chunk_size: int, upload_chunk_size: int = 4194304,
                                 num_workers: int = 4) -> None:
        """Method to run the async upload pipeline

        Args:
            object_service_root: The root URL to use for all objects, including the namespace and dataset name
            object_service_headers: The headers to use when requesting signed urls, including auth info
            objects: A list of PushObjects to push
            progress_update_fn: A callable with arg "completed_bytes" (int) indicating how many bytes have been
                                uploaded in since last called
            multipart_chunk_size: Size in bytes for break a file apart for multi-part uploading
            upload_chunk_size: Size in bytes for streaming IO chunks
            num_workers: the number of consumer workers to start

        Returns:

        """
        # We use a LifoQueue to ensure S3 uploads start as soon as they are ready to help ensure pre-signed urls do
        # not timeout before they can be used if there are a lot of files.
        queue: asyncio.LifoQueue = asyncio.LifoQueue()

        async with aiohttp.ClientSession() as session:
            # Start workers
            workers = []
            for i in range(num_workers):
                task = asyncio.ensure_future(self._push_object_consumer(queue, session, progress_update_fn))
                workers.append(task)

            # Populate the work queue
            await self._push_object_producer(queue,
                                             object_service_root,
                                             object_service_headers,
                                             multipart_chunk_size,
                                             upload_chunk_size,
                                             objects)

            # wait until the consumer has processed all items
            await queue.join()

            # the workers are still awaiting for work so close them
            for worker in workers:
                worker.cancel()

    def push_objects(self, dataset: Dataset, objects: List[PushObject],
                     progress_update_fn: Callable) -> PushResult:
        """High-level method to push objects to the object service/s3

        Args:
            dataset: The current dataset
            objects: A list of PushObjects the enumerate objects to push
            progress_update_fn: A callable with arg "completed_bytes" (int) indicating how many bytes have been
                                uploaded in since last called

        Returns:
            PushResult
        """
        # Clear lists
        self.successful_requests = list()
        self.failed_requests = list()
        message = "Successfully synced all objects"

        backend_config = dataset.client_config.config['datasets']['backends']['gigantum_object_v1']
        upload_chunk_size = backend_config['upload_chunk_size']
        multipart_chunk_size = backend_config['multipart_chunk_size']
        num_workers = backend_config['num_workers']

        object_service_root = f"{self._object_service_endpoint(dataset)}/{dataset.namespace}/{dataset.name}"

        loop = get_event_loop()
        loop.run_until_complete(self._run_push_pipeline(object_service_root, self._object_service_headers(), objects,
                                                        progress_update_fn=progress_update_fn,
                                                        multipart_chunk_size=multipart_chunk_size,
                                                        upload_chunk_size=upload_chunk_size,
                                                        num_workers=num_workers))

        successes = [x.object_details for x in self.successful_requests]

        failures = list()
        for f in self.failed_requests:
            # An exception was raised during task processing
            logger.error(f"Failed to push {f.object_details.dataset_path}:{f.object_details.object_path}")
            message = "Some objects failed to upload and will be retried on the next sync operation. Check results."
            failures.append(f.object_details)

        return PushResult(success=successes, failure=failures, message=message)

    async def _pull_object_consumer(self, queue: asyncio.LifoQueue, session: aiohttp.ClientSession,
                                    progress_update_fn: Callable) -> None:
        """Async Queue consumer worker for downloading objects from the object service/s3

        Args:
            queue: The current work queue
            session: The current aiohttp session
            progress_update_fn: A callable with arg "completed_bytes" (int) indicating how many bytes have been
                                downloaded in since last called

        Returns:
            None
        """
        while True:
            presigned_request: PresignedS3Download = await queue.get()

            try:
                if not presigned_request.is_presigned:
                    # Fetch the signed URL
                    await presigned_request.get_presigned_s3_url(session)
                    queue.put_nowait(presigned_request)
                else:
                    # Process S3 Download
                    await presigned_request.get_object(session, progress_update_fn)
                    self.successful_requests.append(presigned_request)

            except Exception as err:
                logger.exception(err)
                self.failed_requests.append(presigned_request)

            # Notify the queue that the item has been processed
            queue.task_done()

    @staticmethod
    async def _pull_object_producer(queue: asyncio.LifoQueue, object_service_root: str, object_service_headers: dict,
                                    download_chunk_size: int, objects: List[PullObject]) -> None:
        """Async method to populate the queue with download requests

        Args:
            queue: The current work queue
            object_service_root: The root URL to use for all objects, including the namespace and dataset name
            object_service_headers: The headers to use when requesting signed urls, including auth info
            download_chunk_size: Size in bytes for streaming IO chunks
            objects: A list of PullObjects to push

        Returns:
            None
        """
        for obj in objects:
            # Create object destination dir if needed
            obj_dir, _ = obj.object_path.rsplit('/', 1)
            os.makedirs(obj_dir, exist_ok=True)  # type: ignore

            # Populate queue with item for object
            presigned_request = PresignedS3Download(object_service_root,
                                                    object_service_headers,
                                                    download_chunk_size,
                                                    obj)
            await queue.put(presigned_request)

    async def _run_pull_pipeline(self, object_service_root: str, object_service_headers: dict,
                                 objects: List[PullObject], progress_update_fn: Callable,
                                 download_chunk_size: int = 4194304, num_workers: int = 4) -> None:
        """Method to run the async download pipeline

        Args:
            object_service_root: The root URL to use for all objects, including the namespace and dataset name
            object_service_headers: The headers to use when requesting signed urls, including auth info
            objects: A list of PushObjects to push
            progress_update_fn: A callable with arg "completed_bytes" (int) indicating how many bytes have been
                                downloaded in since last called
            download_chunk_size: Size in bytes for streaming IO chunks
            num_workers: the number of consumer workers to start

        Returns:

        """
        # We use a LifoQueue to ensure S3 uploads start as soon as they are ready to help ensure pre-signed urls do
        # not timeout before they can be used if there are a lot of files.
        queue: asyncio.LifoQueue = asyncio.LifoQueue()

        async with aiohttp.ClientSession() as session:
            workers = []
            for i in range(num_workers):
                task = asyncio.ensure_future(self._pull_object_consumer(queue, session, progress_update_fn))
                workers.append(task)

            # Populate the work queue
            await self._pull_object_producer(queue,
                                             object_service_root,
                                             object_service_headers,
                                             download_chunk_size,
                                             objects)

            # wait until the consumer has processed all items
            await queue.join()

            # the workers are still awaiting for work so close them
            for worker in workers:
                worker.cancel()

    def pull_objects(self, dataset: Dataset, objects: List[PullObject],
                     progress_update_fn: Callable) -> PullResult:
        """High-level method to pull objects from the object service/s3

        Args:
            dataset: The current dataset
            objects: A list of PullObjects the enumerate objects to push
            progress_update_fn: A callable with arg "completed_bytes" (int) indicating how many bytes have been
                                downloaded in since last called
        Returns:
            PushResult
        """
        # Clear lists
        self.successful_requests = list()
        self.failed_requests = list()
        message = "Successfully synced all objects"

        backend_config = dataset.client_config.config['datasets']['backends']['gigantum_object_v1']
        download_chunk_size = backend_config['download_chunk_size']
        num_workers = backend_config['num_workers']

        object_service_root = f"{self._object_service_endpoint(dataset)}/{dataset.namespace}/{dataset.name}"

        loop = get_event_loop()
        loop.run_until_complete(self._run_pull_pipeline(object_service_root, self._object_service_headers(), objects,
                                                        progress_update_fn=progress_update_fn,
                                                        download_chunk_size=download_chunk_size,
                                                        num_workers=num_workers))

        successes = [x.object_details for x in self.successful_requests]

        failures = list()
        for f in self.failed_requests:
            # An exception was raised during task processing
            logger.error(f"Failed to pull {f.object_details.dataset_path}:{f.object_details.object_path}")
            message = "Some objects failed to download and will be retried on the next sync operation. Check results."
            failures.append(f.object_details)

        return PullResult(success=successes, failure=failures, message=message)

    def delete_contents(self, dataset) -> None:
        """Method to remove the contents of a dataset from the storage backend, should only work if managed

        Args:
            dataset: Dataset object

        Returns:
            None
        """
        url = f"{self._object_service_endpoint(dataset)}/{dataset.namespace}/{dataset.name}"
        response = requests.delete(url, headers=self._object_service_headers(), timeout=30)

        if response.status_code != 200:
            logger.error(f"Failed to remove {dataset.namespace}/{dataset.name} from cloud index. "
                         f"Status Code: {response.status_code}")
            logger.error(response.json())
            raise IOError("Failed to invoke dataset delete in the dataset backend service.")
        else:
            logger.info(f"Deleted remote repository {dataset.namespace}/{dataset.name} from cloud index")
