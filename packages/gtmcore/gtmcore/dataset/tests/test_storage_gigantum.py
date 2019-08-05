import pytest
from aioresponses import aioresponses
import aiohttp
import snappy
import shutil
import responses
import tempfile
import random
import string
import os
import uuid

from gtmcore.dataset.storage import get_storage_backend
from gtmcore.dataset.storage.gigantum import GigantumObjectStore, PresignedS3Download, PresignedS3Upload
from gtmcore.fixtures.datasets import mock_dataset_with_cache_dir, helper_compress_file
from gtmcore.dataset.io import PushResult, PushObject, PullResult, PullObject


def helper_write_object(directory, object_id, contents):
    object_file = os.path.join(directory, object_id)
    with open(object_file, 'wt') as temp:
        temp.write(f'dummy data: {contents}')

    return object_file


@pytest.fixture()
def helper_write_large_file():
    temp_file_name = os.path.join('/tmp', 'object', uuid.uuid4().hex)
    os.makedirs(os.path.join('/tmp', 'object'), exist_ok=True)
    with open(temp_file_name, 'wt') as tf:
        tf.write(''.join(random.choices(string.ascii_uppercase + string.digits, k=(60 * (10 ** 6)))))
        tf.flush()

    yield temp_file_name
    if os.path.exists(temp_file_name):
        os.remove(temp_file_name)


@pytest.fixture()
def helper_write_two_part_file():
    temp_file_name = os.path.join('/tmp', 'object', uuid.uuid4().hex)
    os.makedirs(os.path.join('/tmp', 'object'), exist_ok=True)
    with open(temp_file_name, 'wt') as tf:
        tf.write(''.join(random.choices(string.ascii_uppercase + string.digits, k=(30 * (10 ** 6)))))
        tf.flush()

    yield temp_file_name
    if os.path.exists(temp_file_name):
        os.remove(temp_file_name)


def chunk_update_callback(completed_bytes: int):
    """Method to update the job's metadata and provide feedback to the UI"""
    assert type(completed_bytes) == int
    assert completed_bytes > 0


@pytest.fixture()
def mock_dataset_head():
    """A pytest fixture that creates a dataset in a temp working dir. Deletes directory after test"""
    with responses.RequestsMock() as rsps:
        rsps.add(responses.HEAD, 'https://api.gigantum.com/object-v1/tester/dataset-1',
                 headers={'x-access-level': 'a'}, status=200)
        yield


@pytest.fixture()
def temp_directories():
    object_dir = f'/tmp/{uuid.uuid4().hex}'
    compressed_dir = f'/tmp/{uuid.uuid4().hex}'
    os.makedirs(object_dir)
    os.makedirs(compressed_dir)
    yield object_dir, compressed_dir,
    shutil.rmtree(object_dir)
    shutil.rmtree(compressed_dir)


class TestStorageBackendGigantum(object):
    def test_get_storage_backend(self):
        sb = get_storage_backend("gigantum_object_v1")

        assert isinstance(sb, GigantumObjectStore)

    def test_get_service_endpoint(self, mock_dataset_with_cache_dir):
        sb = get_storage_backend("gigantum_object_v1")
        ds = mock_dataset_with_cache_dir[0]

        assert sb._object_service_endpoint(ds) == "https://api.gigantum.com/object-v1"

    def test_get_request_headers(self):
        sb = get_storage_backend("gigantum_object_v1")
        sb.set_default_configuration("test-user", "abcd", '1234')

        headers = sb._object_service_headers()

        assert headers['Authorization'] == "Bearer abcd"
        assert headers['Identity'] == "1234"
        assert headers['Accept'] == 'application/json'
        assert headers['Content-Type'] == 'application/json'

    def test_client_should_dedup_on_push(self, mock_dataset_with_cache_dir):
        sb = get_storage_backend("gigantum_object_v1")
        ds = mock_dataset_with_cache_dir[0]

        assert sb.client_should_dedup_on_push is True

    def test_backend_config(self, mock_dataset_with_cache_dir):
        sb = get_storage_backend("gigantum_object_v1")
        ds = mock_dataset_with_cache_dir[0]

        assert sb.is_configured is False

        missing = sb.missing_configuration
        assert len(missing) == 3
        assert missing[0]['parameter'] == "username"

        # Configure 1 param
        sb.configuration['username'] = "test"

        assert sb.is_configured is False
        missing = sb.missing_configuration
        assert len(missing) == 2
        assert missing[0]['parameter'] == "gigantum_bearer_token"

        # Configure all
        sb.set_default_configuration('test', 'asdf', '1234')
        assert sb.is_configured is True

        assert sb.confirm_configuration(ds) is None

    @pytest.mark.asyncio
    async def test_presigneds3upload_get_presigned_s3_url(self, event_loop, mock_dataset_with_cache_dir):
        sb = get_storage_backend("gigantum_object_v1")
        sb.set_default_configuration("test-user", "abcd", '1234')
        ds = mock_dataset_with_cache_dir[0]

        object_service_root = f"{sb._object_service_endpoint(ds)}/{ds.namespace}/{ds.name}"

        headers = sb._object_service_headers()
        upload_chunk_size = 40000
        multipart_chunk_size = 4000000

        with tempfile.NamedTemporaryFile() as tf:
            object_id = os.path.basename(tf.name)
            object_details = PushObject(object_path=tf.name,
                                        revision=ds.git.repo.head.commit.hexsha,
                                        dataset_path='myfile1.txt')
            psu = PresignedS3Upload(object_service_root, headers, multipart_chunk_size, upload_chunk_size, object_details)

            with aioresponses() as mocked_responses:
                async with aiohttp.ClientSession() as session:
                    mocked_responses.put(f'https://api.gigantum.com/object-v1/{ds.namespace}/{ds.name}/{object_id}',
                                         payload={
                                             "presigned_url": "https://dummyurl.com?params=1",
                                             "key_id": "asdfasdf",
                                             "namespace": ds.namespace,
                                             "obj_id": object_id,
                                             "dataset": ds.name
                                         },
                                         status=200)

                    await psu.get_presigned_s3_url(session)

        assert psu.presigned_s3_url == "https://dummyurl.com?params=1"
        assert psu.s3_headers['x-amz-server-side-encryption-aws-kms-key-id'] == "asdfasdf"
        assert psu.skip_object is False

    @pytest.mark.asyncio
    async def test_presigneds3upload_get_presigned_s3_url_multipart(self, event_loop, mock_dataset_with_cache_dir,
                                                                    helper_write_large_file):
        sb = get_storage_backend("gigantum_object_v1")
        sb.set_default_configuration("test-user", "abcd", '1234')
        ds = mock_dataset_with_cache_dir[0]

        object_service_root = f"{sb._object_service_endpoint(ds)}/{ds.namespace}/{ds.name}"

        headers = sb._object_service_headers()

        backend_config = ds.client_config.config['datasets']['backends']['gigantum_object_v1']
        upload_chunk_size = backend_config['upload_chunk_size']
        multipart_chunk_size = backend_config['multipart_chunk_size']

        object_id = os.path.basename(helper_write_large_file)

        object_details = PushObject(object_path=helper_write_large_file,
                                    revision=ds.git.repo.head.commit.hexsha,
                                    dataset_path='myfile1.txt')
        psu = PresignedS3Upload(object_service_root, headers, multipart_chunk_size, upload_chunk_size,
                                object_details)

        assert psu.is_multipart is True

        with aioresponses() as mocked_responses:
            async with aiohttp.ClientSession() as session:
                mocked_responses.post(
                    f'https://api.gigantum.com/object-v1/{ds.namespace}/{ds.name}/{object_id}/multipart',
                    payload={},
                    status=500)
                mocked_responses.post(
                    f'https://api.gigantum.com/object-v1/{ds.namespace}/{ds.name}/{object_id}/multipart',
                    payload={
                        "namespace": ds.namespace,
                        "key_id": "hghghg",
                        "obj_id": object_id,
                        "dataset": ds.name,
                        "upload_id": 'fakeid123'
                    },
                    status=200)

                mocked_responses.put(f'https://api.gigantum.com/object-v1/{ds.namespace}/{ds.name}/{object_id}/'
                                     f'multipart/fakeid123/part/1',
                                     payload={
                                         "presigned_url": "https://dummyurl.com?params=1",
                                         "key_id": "asdfasdf",
                                         "namespace": ds.namespace,
                                         "obj_id": object_id,
                                         "dataset": ds.name
                                     },
                                     status=200)

                with pytest.raises(ValueError):
                    # can't get the URL for a multipart without first creating the upload
                    await psu.get_presigned_s3_url(session)

                assert psu.multipart_upload_id is None
                await psu.prepare_multipart_upload(session)
                assert psu.multipart_upload_id == 'fakeid123'
                assert psu._multipart_completed_parts == list()
                assert len(psu._multipart_parts) == 4
                assert psu._multipart_parts[0].part_number == 1
                assert psu._multipart_parts[0].start_byte == 0
                assert psu._multipart_parts[0].end_byte == multipart_chunk_size
                assert psu._multipart_parts[1].part_number == 2
                assert psu._multipart_parts[1].start_byte == multipart_chunk_size
                assert psu._multipart_parts[1].end_byte == multipart_chunk_size * 2
                assert psu._multipart_parts[2].part_number == 3
                assert psu._multipart_parts[2].start_byte == multipart_chunk_size * 2
                assert psu._multipart_parts[2].end_byte == multipart_chunk_size * 3
                assert psu._multipart_parts[3].part_number == 4
                assert psu._multipart_parts[3].start_byte == multipart_chunk_size * 3
                assert psu._multipart_parts[3].end_byte < multipart_chunk_size * 4
                assert psu._multipart_parts[3].end_byte > multipart_chunk_size * 3

                await psu.get_presigned_s3_url(session)

                assert psu.presigned_s3_url == "https://dummyurl.com?params=1"
                assert psu.s3_headers == dict()
                assert psu.skip_object is False

    @pytest.mark.asyncio
    async def test_presigneds3upload_get_presigned_s3_url_skip(self, event_loop, mock_dataset_with_cache_dir):
        sb = get_storage_backend("gigantum_object_v1")
        sb.set_default_configuration("test-user", "abcd", '1234')
        ds = mock_dataset_with_cache_dir[0]

        with tempfile.NamedTemporaryFile() as tf:
            object_id = os.path.basename(tf.name)
            object_service_root = f"{sb._object_service_endpoint(ds)}/{ds.namespace}/{ds.name}"

            headers = sb._object_service_headers()
            upload_chunk_size = 40000
            multipart_chunk_size = 4000000
            object_details = PushObject(object_path=f"/tmp/{object_id}",
                                        revision=ds.git.repo.head.commit.hexsha,
                                        dataset_path='myfile1.txt')
            psu = PresignedS3Upload(object_service_root, headers, multipart_chunk_size, upload_chunk_size, object_details)

            with aioresponses() as mocked_responses:
                async with aiohttp.ClientSession() as session:
                    mocked_responses.put(f'https://api.gigantum.com/object-v1/{ds.namespace}/{ds.name}/{object_id}',
                                         payload={
                                             "presigned_url": "https://dummyurl.com?params=1",
                                             "key_id": "asdfasdf",
                                             "namespace": ds.namespace,
                                             "obj_id": object_id,
                                             "dataset": ds.name
                                         },
                                         status=403)

                    await psu.get_presigned_s3_url(session)

            assert psu.presigned_s3_url == ""
            assert psu.skip_object is True

    @pytest.mark.asyncio
    async def test_presigneds3upload_get_presigned_s3_url_error(self, event_loop, mock_dataset_with_cache_dir):
        sb = get_storage_backend("gigantum_object_v1")
        sb.set_default_configuration("test-user", "abcd", '1234')
        ds = mock_dataset_with_cache_dir[0]

        with tempfile.NamedTemporaryFile() as tf:
            object_id = os.path.basename(tf.name)
            object_service_root = f"{sb._object_service_endpoint(ds)}/{ds.namespace}/{ds.name}"

            headers = sb._object_service_headers()
            upload_chunk_size = 40000
            multipart_chunk_size = 4000000
            object_details = PushObject(object_path=f"/tmp/{object_id}",
                                        revision=ds.git.repo.head.commit.hexsha,
                                        dataset_path='myfile1.txt')
            psu = PresignedS3Upload(object_service_root, headers, multipart_chunk_size, upload_chunk_size, object_details)

            with aioresponses() as mocked_responses:
                async with aiohttp.ClientSession() as session:
                    mocked_responses.put(f'https://api.gigantum.com/object-v1/{ds.namespace}/{ds.name}/{object_id}',
                                         status=500)
                    mocked_responses.put(f'https://api.gigantum.com/object-v1/{ds.namespace}/{ds.name}/{object_id}',
                                         status=500)
                    mocked_responses.put(f'https://api.gigantum.com/object-v1/{ds.namespace}/{ds.name}/{object_id}',
                                         status=500)
                    with pytest.raises(IOError):
                        await psu.get_presigned_s3_url(session)

    @pytest.mark.asyncio
    async def test_presigneds3download_get_presigned_s3_url(self, event_loop, mock_dataset_with_cache_dir):
        sb = get_storage_backend("gigantum_object_v1")
        sb.set_default_configuration("test-user", "abcd", '1234')
        ds = mock_dataset_with_cache_dir[0]

        object_id = "abcd1234"
        object_service_root = f"{sb._object_service_endpoint(ds)}/{ds.namespace}/{ds.name}"

        headers = sb._object_service_headers()
        download_chunk_size = 40000
        object_details = PullObject(object_path=f"/tmp/{object_id}",
                                    revision=ds.git.repo.head.commit.hexsha,
                                    dataset_path='myfile1.txt')
        psu = PresignedS3Download(object_service_root, headers, download_chunk_size, object_details)

        with aioresponses() as mocked_responses:
            async with aiohttp.ClientSession() as session:
                mocked_responses.get(f'https://api.gigantum.com/object-v1/{ds.namespace}/{ds.name}/{object_id}',
                                     payload={
                                         "presigned_url": "https://dummyurl.com?params=2",
                                         "namespace": ds.namespace,
                                         "obj_id": object_id,
                                         "dataset": ds.name
                                     },
                                     status=200)

                await psu.get_presigned_s3_url(session)

        assert psu.presigned_s3_url == "https://dummyurl.com?params=2"

    @pytest.mark.asyncio
    async def test_presigneds3download_get_presigned_s3_url_error(self, event_loop, mock_dataset_with_cache_dir):
        sb = get_storage_backend("gigantum_object_v1")
        sb.set_default_configuration("test-user", "abcd", '1234')
        ds = mock_dataset_with_cache_dir[0]

        object_id = "abcd1234"
        object_service_root = f"{sb._object_service_endpoint(ds)}/{ds.namespace}/{ds.name}"

        headers = sb._object_service_headers()
        download_chunk_size = 40000
        object_details = PullObject(object_path=f"/tmp/{object_id}",
                                    revision=ds.git.repo.head.commit.hexsha,
                                    dataset_path='myfile1.txt')
        psu = PresignedS3Download(object_service_root, headers, download_chunk_size, object_details)

        with aioresponses() as mocked_responses:
            async with aiohttp.ClientSession() as session:
                mocked_responses.get(f'https://api.gigantum.com/object-v1/{ds.namespace}/{ds.name}/{object_id}',
                                     payload={
                                         "presigned_url": "https://dummyurl.com?params=2",
                                         "namespace": ds.namespace,
                                         "obj_id": object_id,
                                         "dataset": ds.name
                                     },
                                     status=500)
                with pytest.raises(IOError):
                    await psu.get_presigned_s3_url(session)

    @responses.activate
    def test_prepare_push_errors(self, mock_dataset_with_cache_dir):
        sb = get_storage_backend("gigantum_object_v1")
        ds = mock_dataset_with_cache_dir[0]

        responses.add(responses.HEAD, f"{sb._object_service_endpoint(ds)}/{ds.namespace}/{ds.name}",
                      headers={'x-access-level': 'r'}, status=200)

        responses.add(responses.HEAD, f"{sb._object_service_endpoint(ds)}/{ds.namespace}/{ds.name}",
                      headers={}, status=200)

        with pytest.raises(ValueError):
            sb.prepare_push(ds, [])

        sb.configuration['username'] = "test-user"
        with pytest.raises(ValueError):
            sb.prepare_push(ds, [])

        sb.configuration['gigantum_bearer_token'] = "asdf"
        with pytest.raises(ValueError):
            sb.prepare_push(ds, [])

        sb.configuration['gigantum_id_token'] = "1234"
        with pytest.raises(IOError):
            # need more than read access to push
            sb.prepare_push(ds, [])

        with pytest.raises(IOError):
            # should not return a header
            sb.prepare_push(ds, [])

    @responses.activate
    def test_prepare_push(self, mock_dataset_with_cache_dir):
        sb = get_storage_backend("gigantum_object_v1")
        ds = mock_dataset_with_cache_dir[0]

        responses.add(responses.HEAD, f"{sb._object_service_endpoint(ds)}/{ds.namespace}/{ds.name}",
                      headers={'x-access-level': 'a'}, status=200)

        sb.set_default_configuration("test-user", "abcd", '1234')
        sb.prepare_push(ds, [])

    def test_push_objects(self, mock_dataset_with_cache_dir, temp_directories):
        with aioresponses() as mocked_responses:
            sb = get_storage_backend("gigantum_object_v1")

            ds = mock_dataset_with_cache_dir[0]

            sb.set_default_configuration(ds.namespace, "abcd", '1234')

            object_dir, compressed_dir = temp_directories

            obj1_id = uuid.uuid4().hex
            obj2_id = uuid.uuid4().hex

            obj1_src_path = helper_write_object(object_dir, obj1_id, 'abcd')
            obj2_src_path = helper_write_object(object_dir, obj2_id, '1234')
            assert os.path.isfile(obj1_src_path) is True
            assert os.path.isfile(obj2_src_path) is True

            objects = [PushObject(object_path=obj1_src_path,
                                  revision=ds.git.repo.head.commit.hexsha,
                                  dataset_path='myfile1.txt'),
                       PushObject(object_path=obj2_src_path,
                                  revision=ds.git.repo.head.commit.hexsha,
                                  dataset_path='myfile2.txt')
                       ]

            mocked_responses.put(f'https://api.gigantum.com/object-v1/{ds.namespace}/{ds.name}/{obj1_id}',
                                 payload={
                                         "presigned_url": f"https://dummyurl.com/{obj1_id}?params=1",
                                         "namespace": ds.namespace,
                                         "key_id": "hghghg",
                                         "obj_id": obj1_id,
                                         "dataset": ds.name
                                 },
                                 status=200)
            mocked_responses.put(f"https://dummyurl.com/{obj1_id}?params=1",
                                 headers={'Etag': 'asdfasf'},
                                 status=200)

            mocked_responses.put(f'https://api.gigantum.com/object-v1/{ds.namespace}/{ds.name}/{obj2_id}',
                                 payload={
                                            "presigned_url": f"https://dummyurl.com/{obj2_id}?params=1",
                                            "namespace": ds.namespace,
                                            "key_id": "hghghg",
                                            "obj_id": obj2_id,
                                            "dataset": ds.name
                                 },
                                 status=200)
            mocked_responses.put(f"https://dummyurl.com/{obj2_id}?params=1",
                                 headers={'Etag': '12341234'},
                                 status=200)

            result = sb.push_objects(ds, objects, chunk_update_callback)
            assert len(result.success) == 2
            assert len(result.failure) == 0
            assert isinstance(result, PushResult) is True
            assert isinstance(result.success[0], PushObject) is True
            assert result.success[0].object_path != result.success[1].object_path
            assert result.success[0].object_path in [obj1_src_path, obj2_src_path]
            assert result.success[1].object_path in [obj1_src_path, obj2_src_path]

    def test_push_objects_with_existing(self, mock_dataset_with_cache_dir, temp_directories):
        with aioresponses() as mocked_responses:
            sb = get_storage_backend("gigantum_object_v1")

            ds = mock_dataset_with_cache_dir[0]

            sb.set_default_configuration(ds.namespace, "abcd", '1234')

            object_dir, compressed_dir = temp_directories

            obj1_id = uuid.uuid4().hex
            obj2_id = uuid.uuid4().hex

            obj1_src_path = helper_write_object(object_dir, obj1_id, 'abcd')
            obj2_src_path = helper_write_object(object_dir, obj2_id, '1234')
            assert os.path.isfile(obj1_src_path) is True
            assert os.path.isfile(obj2_src_path) is True

            objects = [PushObject(object_path=obj1_src_path,
                                  revision=ds.git.repo.head.commit.hexsha,
                                  dataset_path='myfile1.txt'),
                       PushObject(object_path=obj2_src_path,
                                  revision=ds.git.repo.head.commit.hexsha,
                                  dataset_path='myfile2.txt')
                       ]

            mocked_responses.put(f'https://api.gigantum.com/object-v1/{ds.namespace}/{ds.name}/{obj1_id}',
                                 payload={
                                         "presigned_url": f"https://dummyurl.com/{obj1_id}?params=1",
                                         "namespace": ds.namespace,
                                         "key_id": "hghghg",
                                         "obj_id": obj1_id,
                                         "dataset": ds.name
                                 },
                                 status=403)

            mocked_responses.put(f'https://api.gigantum.com/object-v1/{ds.namespace}/{ds.name}/{obj2_id}',
                                 payload={
                                            "presigned_url": f"https://dummyurl.com/{obj2_id}?params=1",
                                            "namespace": ds.namespace,
                                            "key_id": "hghghg",
                                            "obj_id": obj2_id,
                                            "dataset": ds.name
                                 },
                                 status=200)
            mocked_responses.put(f"https://dummyurl.com/{obj2_id}?params=1",
                                 headers={'Etag': '12341234'},
                                 status=200)

            result = sb.push_objects(ds, objects, chunk_update_callback)
            assert len(result.success) == 2
            assert len(result.failure) == 0
            assert isinstance(result, PushResult) is True
            assert isinstance(result.success[0], PushObject) is True
            assert result.success[0].object_path != result.success[1].object_path
            assert result.success[0].object_path in [obj1_src_path, obj2_src_path]
            assert result.success[1].object_path in [obj1_src_path, obj2_src_path]

    def test_push_objects_fail_url(self, mock_dataset_with_cache_dir, temp_directories):
        with aioresponses() as mocked_responses:
            sb = get_storage_backend("gigantum_object_v1")

            ds = mock_dataset_with_cache_dir[0]

            sb.set_default_configuration(ds.namespace, "abcd", '1234')

            object_dir, compressed_dir = temp_directories

            obj1_id = uuid.uuid4().hex
            obj2_id = uuid.uuid4().hex

            obj1_src_path = helper_write_object(object_dir, obj1_id, 'abcd')
            obj2_src_path = helper_write_object(object_dir, obj2_id, '1234')
            assert os.path.isfile(obj1_src_path) is True
            assert os.path.isfile(obj2_src_path) is True

            objects = [PushObject(object_path=obj1_src_path,
                                  revision=ds.git.repo.head.commit.hexsha,
                                  dataset_path='myfile1.txt'),
                       PushObject(object_path=obj2_src_path,
                                  revision=ds.git.repo.head.commit.hexsha,
                                  dataset_path='myfile2.txt')
                       ]

            mocked_responses.put(f'https://api.gigantum.com/object-v1/{ds.namespace}/{ds.name}/{obj1_id}',
                                 payload={
                                         "presigned_url": f"https://dummyurl.com/{obj1_id}?params=1",
                                         "namespace": ds.namespace,
                                         "key_id": "hghghg",
                                         "obj_id": obj1_id,
                                         "dataset": ds.name
                                 },
                                 status=400)

            mocked_responses.put(f'https://api.gigantum.com/object-v1/{ds.namespace}/{ds.name}/{obj2_id}',
                                 payload={
                                            "presigned_url": f"https://dummyurl.com/{obj2_id}?params=1",
                                            "namespace": ds.namespace,
                                            "key_id": "hghghg",
                                            "obj_id": obj2_id,
                                            "dataset": ds.name
                                 },
                                 status=200)
            mocked_responses.put(f"https://dummyurl.com/{obj2_id}?params=1",
                                 headers={'Etag': '12341234'},
                                 status=200)

            result = sb.push_objects(ds, objects, chunk_update_callback)
            assert len(result.success) == 1
            assert len(result.failure) == 1
            assert isinstance(result, PushResult) is True
            assert isinstance(result.success[0], PushObject) is True
            assert result.success[0].object_path == obj2_src_path
            assert result.failure[0].object_path == obj1_src_path

    def test_push_objects_fail_upload(self, mock_dataset_with_cache_dir, temp_directories):
        with aioresponses() as mocked_responses:
            sb = get_storage_backend("gigantum_object_v1")

            ds = mock_dataset_with_cache_dir[0]

            sb.set_default_configuration(ds.namespace, "abcd", '1234')

            object_dir, compressed_dir = temp_directories

            obj1_id = uuid.uuid4().hex
            obj2_id = uuid.uuid4().hex

            obj1_src_path = helper_write_object(object_dir, obj1_id, 'abcd')
            obj2_src_path = helper_write_object(object_dir, obj2_id, '1234')
            assert os.path.isfile(obj1_src_path) is True
            assert os.path.isfile(obj2_src_path) is True

            objects = [PushObject(object_path=obj1_src_path,
                                  revision=ds.git.repo.head.commit.hexsha,
                                  dataset_path='myfile1.txt'),
                       PushObject(object_path=obj2_src_path,
                                  revision=ds.git.repo.head.commit.hexsha,
                                  dataset_path='myfile2.txt')
                       ]

            mocked_responses.put(f'https://api.gigantum.com/object-v1/{ds.namespace}/{ds.name}/{obj1_id}',
                                 payload={
                                         "presigned_url": f"https://dummyurl.com/{obj1_id}?params=1",
                                         "namespace": ds.namespace,
                                         "key_id": "hghghg",
                                         "obj_id": obj1_id,
                                         "dataset": ds.name
                                 },
                                 status=200)
            mocked_responses.put(f"https://dummyurl.com/{obj1_id}?params=1",
                                 headers={'Etag': 'asdfasdf'},
                                 status=200)

            mocked_responses.put(f'https://api.gigantum.com/object-v1/{ds.namespace}/{ds.name}/{obj2_id}',
                                 payload={
                                            "presigned_url": f"https://dummyurl.com/{obj2_id}?params=1",
                                            "namespace": ds.namespace,
                                            "key_id": "hghghg",
                                            "obj_id": obj2_id,
                                            "dataset": ds.name
                                 },
                                 status=200)
            mocked_responses.put(f"https://dummyurl.com/{obj2_id}?params=1",
                                 status=500)
            mocked_responses.put(f"https://dummyurl.com/{obj2_id}?params=1",
                                 status=500)
            mocked_responses.put(f"https://dummyurl.com/{obj2_id}?params=1",
                                 status=500)

            result = sb.push_objects(ds, objects, chunk_update_callback)
            assert len(result.success) == 1
            assert len(result.failure) == 1
            assert isinstance(result, PushResult) is True
            assert isinstance(result.success[0], PushObject) is True
            assert result.success[0].object_path == obj1_src_path
            assert result.failure[0].object_path == obj2_src_path

    def test_finalize_push(self, mock_dataset_with_cache_dir):
        sb = get_storage_backend("gigantum_object_v1")
        ds = mock_dataset_with_cache_dir[0]
        sb.finalize_push(ds)

    @responses.activate
    def test_prepare_pull(self, mock_dataset_with_cache_dir):
        sb = get_storage_backend("gigantum_object_v1")
        ds = mock_dataset_with_cache_dir[0]

        responses.add(responses.HEAD, f"{sb._object_service_endpoint(ds)}/{ds.namespace}/{ds.name}",
                      headers={}, status=404)

        responses.add(responses.HEAD, f"{sb._object_service_endpoint(ds)}/{ds.namespace}/{ds.name}",
                      headers={'x-access-level': 'r'}, status=200)

        with pytest.raises(ValueError):
            sb.prepare_pull(ds, [])

        sb.configuration['username'] = "test-user"
        with pytest.raises(ValueError):
            sb.prepare_pull(ds, [])

        sb.configuration['gigantum_bearer_token'] = "asdf"
        with pytest.raises(ValueError):
            sb.prepare_pull(ds, [])

        sb.configuration['gigantum_id_token'] = "1234"

        with pytest.raises(IOError):
            # missing header
            sb.prepare_pull(ds, [])

        sb.prepare_pull(ds, [])

    def test_pull_objects(self, mock_dataset_with_cache_dir, temp_directories):
        with aioresponses() as mocked_responses:
            sb = get_storage_backend("gigantum_object_v1")
            ds = mock_dataset_with_cache_dir[0]
            sb.set_default_configuration(ds.namespace, "abcd", '1234')

            object_dir, compressed_dir = temp_directories

            obj1_id = uuid.uuid4().hex
            obj2_id = uuid.uuid4().hex

            obj1_src_path = helper_write_object(object_dir, obj1_id, 'abcd')
            obj2_src_path = helper_write_object(object_dir, obj2_id, '1234')
            assert os.path.isfile(obj1_src_path) is True
            assert os.path.isfile(obj2_src_path) is True

            obj1_compressed_path = os.path.join(compressed_dir, obj1_id)
            obj2_compressed_path = os.path.join(compressed_dir, obj2_id)
            helper_compress_file(obj1_src_path, obj1_compressed_path)
            helper_compress_file(obj2_src_path, obj2_compressed_path)

            assert os.path.isfile(obj1_src_path) is False
            assert os.path.isfile(obj2_src_path) is False
            assert os.path.isfile(obj1_compressed_path) is True
            assert os.path.isfile(obj2_compressed_path) is True

            check_info = {obj1_src_path: obj1_compressed_path,
                          obj2_src_path: obj2_compressed_path}

            objects = [PullObject(object_path=obj1_src_path,
                                  revision=ds.git.repo.head.commit.hexsha,
                                  dataset_path='myfile1.txt'),
                       PullObject(object_path=obj2_src_path,
                                  revision=ds.git.repo.head.commit.hexsha,
                                  dataset_path='myfile2.txt')
                       ]

            mocked_responses.get(f'https://api.gigantum.com/object-v1/{ds.namespace}/{ds.name}/{obj1_id}',
                                 payload={
                                         "presigned_url": f"https://dummyurl.com/{obj1_id}?params=1",
                                         "namespace": ds.namespace,
                                         "obj_id": obj1_id,
                                         "dataset": ds.name
                                 },
                                 status=200)

            with open(obj1_compressed_path, 'rb') as data1:
                mocked_responses.get(f"https://dummyurl.com/{obj1_id}?params=1",
                                     body=data1.read(), status=200,
                                     content_type='application/octet-stream')

            mocked_responses.get(f'https://api.gigantum.com/object-v1/{ds.namespace}/{ds.name}/{obj2_id}',
                                 payload={
                                         "presigned_url": f"https://dummyurl.com/{obj2_id}?params=1",
                                         "namespace": ds.namespace,
                                         "obj_id": obj2_id,
                                         "dataset": ds.name
                                 },
                                 status=200)

            with open(obj2_compressed_path, 'rb') as data2:
                mocked_responses.get(f"https://dummyurl.com/{obj2_id}?params=1",
                                     body=data2.read(), status=200,
                                     content_type='application/octet-stream')

            result = sb.pull_objects(ds, objects, chunk_update_callback)
            assert len(result.success) == 2
            assert len(result.failure) == 0
            assert isinstance(result, PullResult) is True
            assert isinstance(result.success[0], PullObject) is True
            assert result.success[0].object_path != result.success[1].object_path
            assert result.success[0].object_path in [obj1_src_path, obj2_src_path]
            assert result.success[1].object_path in [obj1_src_path, obj2_src_path]

            assert os.path.isfile(obj1_src_path) is True
            assert os.path.isfile(obj2_src_path) is True

            decompressor = snappy.StreamDecompressor()
            for r in result.success:
                with open(check_info[r.object_path], 'rb') as dd:
                    source1 = decompressor.decompress(dd.read())
                    source1 += decompressor.flush()
                with open(r.object_path, 'rt') as dd:
                    dest1 = dd.read()
                assert source1.decode("utf-8") == dest1

    def test_pull_objects_fail_download(self, mock_dataset_with_cache_dir, temp_directories):
        with aioresponses() as mocked_responses:
            sb = get_storage_backend("gigantum_object_v1")
            ds = mock_dataset_with_cache_dir[0]
            sb.set_default_configuration(ds.namespace, "abcd", '1234')

            object_dir, compressed_dir = temp_directories

            obj1_id = uuid.uuid4().hex
            obj2_id = uuid.uuid4().hex

            obj1_src_path = helper_write_object(object_dir, obj1_id, 'abcd')
            obj2_src_path = helper_write_object(object_dir, obj2_id, '1234')
            assert os.path.isfile(obj1_src_path) is True
            assert os.path.isfile(obj2_src_path) is True

            obj1_compressed_path = os.path.join(compressed_dir, obj1_id)
            obj2_compressed_path = os.path.join(compressed_dir, obj2_id)
            helper_compress_file(obj1_src_path, obj1_compressed_path)
            helper_compress_file(obj2_src_path, obj2_compressed_path)

            assert os.path.isfile(obj1_src_path) is False
            assert os.path.isfile(obj2_src_path) is False
            assert os.path.isfile(obj1_compressed_path) is True
            assert os.path.isfile(obj2_compressed_path) is True

            check_info = {obj1_src_path: obj1_compressed_path,
                          obj2_src_path: obj2_compressed_path}

            objects = [PullObject(object_path=obj1_src_path,
                                  revision=ds.git.repo.head.commit.hexsha,
                                  dataset_path='myfile1.txt'),
                       PullObject(object_path=obj2_src_path,
                                  revision=ds.git.repo.head.commit.hexsha,
                                  dataset_path='myfile2.txt')
                       ]

            mocked_responses.get(f'https://api.gigantum.com/object-v1/{ds.namespace}/{ds.name}/{obj1_id}',
                                 payload={
                                         "presigned_url": f"https://dummyurl.com/{obj1_id}?params=1",
                                         "namespace": ds.namespace,
                                         "obj_id": obj1_id,
                                         "dataset": ds.name
                                 },
                                 status=200)

            mocked_responses.get(f"https://dummyurl.com/{obj1_id}?params=1", status=500,
                                 content_type='application/octet-stream')

            mocked_responses.get(f'https://api.gigantum.com/object-v1/{ds.namespace}/{ds.name}/{obj2_id}',
                                 payload={
                                         "presigned_url": f"https://dummyurl.com/{obj2_id}?params=1",
                                         "namespace": ds.namespace,
                                         "obj_id": obj2_id,
                                         "dataset": ds.name
                                 },
                                 status=200)

            with open(obj2_compressed_path, 'rb') as data2:
                mocked_responses.get(f"https://dummyurl.com/{obj2_id}?params=1",
                                     body=data2.read(), status=200,
                                     content_type='application/octet-stream')

            result = sb.pull_objects(ds, objects, chunk_update_callback)
            assert len(result.success) == 1
            assert len(result.failure) == 1
            assert isinstance(result, PullResult) is True
            assert isinstance(result.success[0], PullObject) is True
            assert result.success[0].object_path == obj2_src_path
            assert result.failure[0].object_path == obj1_src_path

            assert os.path.isfile(result.success[0].object_path) is True
            assert os.path.isfile(result.failure[0].object_path) is False

            decompressor = snappy.StreamDecompressor()
            with open(check_info[result.success[0].object_path], 'rb') as dd:
                source1 = decompressor.decompress(dd.read())
                source1 += decompressor.flush()
            with open(result.success[0].object_path, 'rt') as dd:
                dest1 = dd.read()
            assert source1.decode("utf-8") == dest1

    def test_pull_objects_fail_signing(self, mock_dataset_with_cache_dir, temp_directories):
        with aioresponses() as mocked_responses:
            sb = get_storage_backend("gigantum_object_v1")
            ds = mock_dataset_with_cache_dir[0]
            sb.set_default_configuration(ds.namespace, "abcd", '1234')

            object_dir, compressed_dir = temp_directories

            obj1_id = uuid.uuid4().hex
            obj2_id = uuid.uuid4().hex

            obj1_src_path = helper_write_object(object_dir, obj1_id, 'abcd')
            obj2_src_path = helper_write_object(object_dir, obj2_id, '1234')
            assert os.path.isfile(obj1_src_path) is True
            assert os.path.isfile(obj2_src_path) is True

            obj1_compressed_path = os.path.join(compressed_dir, obj1_id)
            obj2_compressed_path = os.path.join(compressed_dir, obj2_id)
            helper_compress_file(obj1_src_path, obj1_compressed_path)
            helper_compress_file(obj2_src_path, obj2_compressed_path)

            assert os.path.isfile(obj1_src_path) is False
            assert os.path.isfile(obj2_src_path) is False
            assert os.path.isfile(obj1_compressed_path) is True
            assert os.path.isfile(obj2_compressed_path) is True

            check_info = {obj1_src_path: obj1_compressed_path,
                          obj2_src_path: obj2_compressed_path}

            objects = [PullObject(object_path=obj1_src_path,
                                  revision=ds.git.repo.head.commit.hexsha,
                                  dataset_path='myfile1.txt'),
                       PullObject(object_path=obj2_src_path,
                                  revision=ds.git.repo.head.commit.hexsha,
                                  dataset_path='myfile2.txt')
                       ]

            mocked_responses.get(f'https://api.gigantum.com/object-v1/{ds.namespace}/{ds.name}/{obj1_id}',
                                 payload={
                                         "presigned_url": f"https://dummyurl.com/{obj1_id}?params=1",
                                         "namespace": ds.namespace,
                                         "obj_id": obj1_id,
                                         "dataset": ds.name
                                 },
                                 status=400)

            mocked_responses.get(f'https://api.gigantum.com/object-v1/{ds.namespace}/{ds.name}/{obj2_id}',
                                 payload={
                                         "presigned_url": f"https://dummyurl.com/{obj2_id}?params=1",
                                         "namespace": ds.namespace,
                                         "obj_id": obj2_id,
                                         "dataset": ds.name
                                 },
                                 status=200)

            with open(obj2_compressed_path, 'rb') as data2:
                mocked_responses.get(f"https://dummyurl.com/{obj2_id}?params=1",
                                     body=data2.read(), status=200,
                                     content_type='application/octet-stream')

            result = sb.pull_objects(ds, objects, chunk_update_callback)
            assert len(result.success) == 1
            assert len(result.failure) == 1
            assert isinstance(result, PullResult) is True
            assert isinstance(result.success[0], PullObject) is True
            assert result.success[0].object_path == obj2_src_path
            assert result.failure[0].object_path == obj1_src_path

            assert os.path.isfile(result.success[0].object_path) is True
            assert os.path.isfile(result.failure[0].object_path) is False

            decompressor = snappy.StreamDecompressor()
            with open(check_info[result.success[0].object_path], 'rb') as dd:
                source1 = decompressor.decompress(dd.read())
                source1 += decompressor.flush()
            with open(result.success[0].object_path, 'rt') as dd:
                dest1 = dd.read()
            assert source1.decode("utf-8") == dest1

    def test_finalize_pull(self, mock_dataset_with_cache_dir):
        sb = get_storage_backend("gigantum_object_v1")
        ds = mock_dataset_with_cache_dir[0]
        sb.finalize_pull(ds)

    def test_push_objects_multipart(self, mock_dataset_with_cache_dir, temp_directories, mock_dataset_head):
        with aioresponses() as mocked_responses:
            sb = get_storage_backend("gigantum_object_v1")

            ds = mock_dataset_with_cache_dir[0]

            sb.set_default_configuration(ds.namespace, "abcd", '1234')

            object_dir, compressed_dir = temp_directories

            obj1_id = uuid.uuid4().hex
            obj2_id = uuid.uuid4().hex

            obj1_src_path = helper_write_object(object_dir, obj1_id, 'abcd')
            obj2_src_path = helper_write_object(object_dir, obj2_id,
                                                ''.join(random.choices(string.ascii_uppercase + string.digits,
                                                                       k=(30 * (10 ** 6)))))
            assert os.path.isfile(obj1_src_path) is True
            assert os.path.isfile(obj2_src_path) is True

            objects = [PushObject(object_path=obj1_src_path,
                                  revision=ds.git.repo.head.commit.hexsha,
                                  dataset_path='myfile1.txt'),
                       PushObject(object_path=obj2_src_path,
                                  revision=ds.git.repo.head.commit.hexsha,
                                  dataset_path='myfile2.txt')
                       ]

            mocked_responses.put(f'https://api.gigantum.com/object-v1/{ds.namespace}/{ds.name}/{obj1_id}',
                                 payload={
                                         "presigned_url": f"https://dummyurl.com/{obj1_id}?params=1",
                                         "namespace": ds.namespace,
                                         "key_id": "hghghg",
                                         "obj_id": obj1_id,
                                         "dataset": ds.name
                                 },
                                 status=200)
            mocked_responses.put(f"https://dummyurl.com/{obj1_id}?params=1",
                                 headers={'Etag': 'asdfasf'},
                                 status=200)

            mocked_responses.post(f'https://api.gigantum.com/object-v1/{ds.namespace}/{ds.name}/{obj2_id}/multipart',
                                 payload={
                                            "namespace": ds.namespace,
                                            "key_id": "hghghg",
                                            "obj_id": obj2_id,
                                            "dataset": ds.name,
                                            "upload_id": 'fakeid123'
                                 },
                                 status=200)

            mocked_responses.put(f'https://api.gigantum.com/object-v1/{ds.namespace}/{ds.name}/{obj2_id}/multipart/'
                                 f'fakeid123/part/1',
                                 payload={
                                            "presigned_url": f"https://dummyurl.com/{obj2_id}?params=1",
                                            "namespace": ds.namespace,
                                            "key_id": "hghghg",
                                            "obj_id": obj2_id,
                                            "dataset": ds.name
                                 },
                                 status=200)

            mocked_responses.put(f'https://api.gigantum.com/object-v1/{ds.namespace}/{ds.name}/{obj2_id}/multipart/'
                                 f'fakeid123/part/2',
                                 payload={
                                            "presigned_url": f"https://dummyurl.com/{obj2_id}?params=2",
                                            "namespace": ds.namespace,
                                            "key_id": "hghghg",
                                            "obj_id": obj2_id,
                                            "dataset": ds.name
                                 },
                                 status=200)
            mocked_responses.put(f"https://dummyurl.com/{obj2_id}?params=1",
                                 headers={'Etag': '12341234'},
                                 status=200)
            mocked_responses.put(f"https://dummyurl.com/{obj2_id}?params=2",
                                 headers={'Etag': 'asdfasdf'},
                                 status=200)

            # Fail complete multipart once to demonstrate retry
            mocked_responses.post(f'https://api.gigantum.com/object-v1/{ds.namespace}/{ds.name}/{obj2_id}/'
                                  f'multipart/fakeid123',
                                  payload={
                                             "namespace": ds.namespace,
                                             "obj_id": obj2_id,
                                             "dataset": ds.name,
                                  },
                                  status=500)

            mocked_responses.post(f'https://api.gigantum.com/object-v1/{ds.namespace}/{ds.name}/{obj2_id}/'
                                  f'multipart/fakeid123',
                                  payload={
                                             "namespace": ds.namespace,
                                             "obj_id": obj2_id,
                                             "dataset": ds.name,
                                  },
                                  status=200)

            sb.prepare_push(ds, objects)
            result = sb.push_objects(ds, objects, chunk_update_callback)
            assert len(result.success) == 2
            assert len(result.failure) == 0
            assert isinstance(result, PushResult) is True
            assert isinstance(result.success[0], PushObject) is True
            assert result.success[0].object_path != result.success[1].object_path
            assert result.success[0].object_path in [obj1_src_path, obj2_src_path]
            assert result.success[1].object_path in [obj1_src_path, obj2_src_path]

    def test_push_objects_multipart_failure(self, mock_dataset_with_cache_dir, temp_directories, mock_dataset_head):
        with aioresponses() as mocked_responses:
            sb = get_storage_backend("gigantum_object_v1")

            ds = mock_dataset_with_cache_dir[0]

            sb.set_default_configuration(ds.namespace, "abcd", '1234')

            object_dir, compressed_dir = temp_directories

            obj1_id = uuid.uuid4().hex
            obj2_id = uuid.uuid4().hex

            obj1_src_path = helper_write_object(object_dir, obj1_id, 'abcd')
            obj2_src_path = helper_write_object(object_dir, obj2_id,
                                                ''.join(random.choices(string.ascii_uppercase + string.digits,
                                                                       k=(60 * (10 ** 6)))))
            assert os.path.isfile(obj1_src_path) is True
            assert os.path.isfile(obj2_src_path) is True

            objects = [PushObject(object_path=obj1_src_path,
                                  revision=ds.git.repo.head.commit.hexsha,
                                  dataset_path='myfile1.txt'),
                       PushObject(object_path=obj2_src_path,
                                  revision=ds.git.repo.head.commit.hexsha,
                                  dataset_path='myfile2.txt')
                       ]

            mocked_responses.put(f'https://api.gigantum.com/object-v1/{ds.namespace}/{ds.name}/{obj1_id}',
                                 payload={
                                         "presigned_url": f"https://dummyurl.com/{obj1_id}?params=1",
                                         "namespace": ds.namespace,
                                         "key_id": "hghghg",
                                         "obj_id": obj1_id,
                                         "dataset": ds.name
                                 },
                                 status=200)
            mocked_responses.put(f"https://dummyurl.com/{obj1_id}?params=1",
                                 headers={'Etag': 'asdfasf'},
                                 status=200)

            mocked_responses.post(f'https://api.gigantum.com/object-v1/{ds.namespace}/{ds.name}/{obj2_id}/multipart',
                                 payload={
                                            "namespace": ds.namespace,
                                            "key_id": "hghghg",
                                            "obj_id": obj2_id,
                                            "dataset": ds.name,
                                            "upload_id": 'fakeid123'
                                 },
                                 status=200)

            mocked_responses.put(f'https://api.gigantum.com/object-v1/{ds.namespace}/{ds.name}/{obj2_id}/multipart/'
                                 f'fakeid123/part/1',
                                 payload={
                                            "presigned_url": f"https://dummyurl.com/{obj2_id}?params=1",
                                            "namespace": ds.namespace,
                                            "key_id": "hghghg",
                                            "obj_id": obj2_id,
                                            "dataset": ds.name
                                 },
                                 status=200)
            mocked_responses.put(f"https://dummyurl.com/{obj2_id}?params=1",
                                 headers={'Etag': '12341234'},
                                 status=200)

            mocked_responses.put(f'https://api.gigantum.com/object-v1/{ds.namespace}/{ds.name}/{obj2_id}/multipart/'
                                 f'fakeid123/part/2',
                                 status=500)
            mocked_responses.put(f'https://api.gigantum.com/object-v1/{ds.namespace}/{ds.name}/{obj2_id}/multipart/'
                                 f'fakeid123/part/2',
                                 status=500)
            mocked_responses.put(f'https://api.gigantum.com/object-v1/{ds.namespace}/{ds.name}/{obj2_id}/multipart/'
                                 f'fakeid123/part/2',
                                 status=500)

            # Fail abort multipart once to test retry
            mocked_responses.delete(f'https://api.gigantum.com/object-v1/{ds.namespace}/{ds.name}/{obj2_id}/'
                                    f'multipart/fakeid123',
                                    status=500)

            mocked_responses.delete(f'https://api.gigantum.com/object-v1/{ds.namespace}/{ds.name}/{obj2_id}/'
                                    f'multipart/fakeid123',
                                    status=204)

            sb.prepare_push(ds, objects)
            result = sb.push_objects(ds, objects, chunk_update_callback)
            assert len(result.success) == 1
            assert len(result.failure) == 1
            assert isinstance(result, PushResult) is True
            assert isinstance(result.success[0], PushObject) is True
            assert result.success[0].object_path == obj1_src_path
            assert result.failure[0].object_path == obj2_src_path
            assert os.path.exists(f'/tmp/{obj2_id}') is False

    @pytest.mark.asyncio
    async def test_presigneds3upload_file_loader(self, event_loop, mock_dataset_with_cache_dir):
        """Test the async generator method used to load data into the request stream"""
        def update_fn(completed_bytes):
            assert completed_bytes > 0

        sb = get_storage_backend("gigantum_object_v1")
        sb.set_default_configuration("test-user", "abcd", '1234')
        ds = mock_dataset_with_cache_dir[0]

        object_service_root = f"{sb._object_service_endpoint(ds)}/{ds.namespace}/{ds.name}"

        headers = sb._object_service_headers()

        backend_config = ds.client_config.config['datasets']['backends']['gigantum_object_v1']
        upload_chunk_size = backend_config['upload_chunk_size']
        multipart_chunk_size = backend_config['multipart_chunk_size']

        object_id = uuid.uuid4().hex
        obj1_src_path = helper_write_object(ds.client_config.app_workdir, object_id,
                                            ''.join(random.choices(string.ascii_uppercase + string.digits,
                                                                   k=(3 * upload_chunk_size + 100))))

        object_details = PushObject(object_path=obj1_src_path,
                                    revision=ds.git.repo.head.commit.hexsha,
                                    dataset_path='myfile1.txt')
        psu = PresignedS3Upload(object_service_root, headers, multipart_chunk_size, upload_chunk_size,
                                object_details)

        assert psu.is_multipart is False
        # the + 12 is because of the string "dummy data: " that's added in the helper function
        assert os.path.getsize(obj1_src_path) == (3 * upload_chunk_size + 100) + 12

        num_chunks = 0
        iterator = psu._file_loader(obj1_src_path, update_fn)
        try:
            while True:
                chunk = await iterator.__anext__()
                num_chunks += 1
                if num_chunks == 4:
                    assert len(chunk) == 112
                else:
                    assert len(chunk) == upload_chunk_size
                if num_chunks > 4:
                    assert "Too many chunks"
        except StopAsyncIteration:
            # Raises StopAsyncIteration when no more byte
            assert num_chunks == 4

    @pytest.mark.asyncio
    async def test_presigneds3upload_file_loader_multipart(self, event_loop, mock_dataset_with_cache_dir,
                                                           helper_write_two_part_file):
        with aioresponses() as mocked_responses:
            def update_fn(completed_bytes):
                assert completed_bytes > 0

            sb = get_storage_backend("gigantum_object_v1")
            sb.set_default_configuration("test-user", "abcd", '1234')
            ds = mock_dataset_with_cache_dir[0]

            object_service_root = f"{sb._object_service_endpoint(ds)}/{ds.namespace}/{ds.name}"

            headers = sb._object_service_headers()

            backend_config = ds.client_config.config['datasets']['backends']['gigantum_object_v1']
            upload_chunk_size = backend_config['upload_chunk_size']
            multipart_chunk_size = backend_config['multipart_chunk_size']

            object_details = PushObject(object_path=helper_write_two_part_file,
                                        revision=ds.git.repo.head.commit.hexsha,
                                        dataset_path='myfile1.txt')
            psu = PresignedS3Upload(object_service_root, headers, multipart_chunk_size, upload_chunk_size,
                                    object_details)

            assert psu.is_multipart is True

            iterator = psu._file_loader(helper_write_two_part_file, update_fn)
            with pytest.raises(ValueError):
                # Multipart upload and you haven't set up the parts yet
                await iterator.__anext__()

            obj2_id = os.path.basename(helper_write_two_part_file)
            mocked_responses.post(f'https://api.gigantum.com/object-v1/{ds.namespace}/{ds.name}/{obj2_id}/multipart',
                                  payload={
                                      "namespace": ds.namespace,
                                      "key_id": "hghghg",
                                      "obj_id": obj2_id,
                                      "dataset": ds.name,
                                      "upload_id": 'fakeid123'
                                  },
                                  status=200)

            # Setup multipart upload
            async with aiohttp.ClientSession() as session:
                await psu.prepare_multipart_upload(session)

            num_chunks = 0
            saved_data = bytes()
            iterator = psu._file_loader(helper_write_two_part_file, update_fn)

            # Do the first chunk
            try:
                while True:
                    chunk = await iterator.__anext__()
                    num_chunks += 1
                    saved_data = saved_data + chunk
                    assert len(chunk) == upload_chunk_size
                    if num_chunks > 16:
                        assert "Too many chunks"
            except StopAsyncIteration:
                # Raises StopAsyncIteration when no more byte
                assert num_chunks == 16

            psu.mark_current_part_complete("fakeetag")

            # Do the second chunk
            num_chunks = 0
            iterator = psu._file_loader(helper_write_two_part_file, update_fn)
            try:
                while True:
                    chunk = await iterator.__anext__()
                    num_chunks += 1
                    saved_data = saved_data + chunk
                    if num_chunks == 13:
                        assert len(chunk) == 639872
                    else:
                        assert len(chunk) == upload_chunk_size
                    if num_chunks > 13:
                        assert "Too many chunks"
            except StopAsyncIteration:
                # Raises StopAsyncIteration when no more byte
                assert num_chunks == 13

            # Make sure the content is correct
            with open(helper_write_two_part_file, 'rb') as source:
                data = source.read()
                assert data == saved_data

    def test_push_objects_multipart_with_skip(self, mock_dataset_with_cache_dir, temp_directories, mock_dataset_head):
        with aioresponses() as mocked_responses:
            sb = get_storage_backend("gigantum_object_v1")

            ds = mock_dataset_with_cache_dir[0]

            sb.set_default_configuration(ds.namespace, "abcd", '1234')

            object_dir, compressed_dir = temp_directories

            obj1_id = uuid.uuid4().hex
            obj2_id = uuid.uuid4().hex

            obj1_src_path = helper_write_object(object_dir, obj1_id, 'abcd')
            obj2_src_path = helper_write_object(object_dir, obj2_id,
                                                ''.join(random.choices(string.ascii_uppercase + string.digits,
                                                                       k=(60 * (10 ** 6)))))
            assert os.path.isfile(obj1_src_path) is True
            assert os.path.isfile(obj2_src_path) is True

            objects = [PushObject(object_path=obj1_src_path,
                                  revision=ds.git.repo.head.commit.hexsha,
                                  dataset_path='myfile1.txt'),
                       PushObject(object_path=obj2_src_path,
                                  revision=ds.git.repo.head.commit.hexsha,
                                  dataset_path='myfile2.txt')
                       ]

            mocked_responses.put(f'https://api.gigantum.com/object-v1/{ds.namespace}/{ds.name}/{obj1_id}',
                                 payload={
                                         "presigned_url": f"https://dummyurl.com/{obj1_id}?params=1",
                                         "namespace": ds.namespace,
                                         "key_id": "hghghg",
                                         "obj_id": obj1_id,
                                         "dataset": ds.name
                                 },
                                 status=200)
            mocked_responses.put(f"https://dummyurl.com/{obj1_id}?params=1",
                                 headers={'Etag': 'asdfasf'},
                                 status=200)

            mocked_responses.post(f'https://api.gigantum.com/object-v1/{ds.namespace}/{ds.name}/{obj2_id}/multipart',
                                  payload={},
                                  status=403)

            sb.prepare_push(ds, objects)
            result = sb.push_objects(ds, objects, chunk_update_callback)
            assert len(result.success) == 2
            assert len(result.failure) == 0
            assert isinstance(result, PushResult) is True
            assert isinstance(result.success[0], PushObject) is True
            assert result.success[0].object_path != result.success[1].object_path
            assert result.success[0].object_path in [obj1_src_path, obj2_src_path]
            assert result.success[1].object_path in [obj1_src_path, obj2_src_path]
