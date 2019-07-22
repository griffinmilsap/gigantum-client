import os
from typing import List, Callable, Optional, Tuple
import subprocess
import glob
from natsort import natsorted
from operator import attrgetter
import math

from gtmcore.dataset.dataset import Dataset
from gtmcore.dataset.manifest import Manifest
from gtmcore.dataset.storage.backend import UnmanagedStorageBackend, ManagedStorageBackend
from gtmcore.dataset.io import PushObject, PushResult, PullResult, PullObject

from gtmcore.logging import LMLogger

logger = LMLogger.get_logger()


class IOManager(object):
    """Class to manage file IO with remote storage backends and glue everything together"""

    def __init__(self, dataset: Dataset, manifest: Manifest) -> None:
        self.dataset = dataset
        self.manifest = manifest

        self.push_dir = os.path.join(self.manifest.cache_mgr.cache_root, 'objects', '.push')

        # Property to keep status state if needed when appending messages
        self._status_msg = ""

    def _commit_in_branch(self, commit_hash: str) -> bool:
        """Method to check if a commit is in the current branch, ignoring the last commit.

        This is used for the purpose of only pushing objects that are part of the current branch. We ignore the last
        commit because objects to push are stored in a file named with the revision at which the files were written.
        This is different from the revision that contains the files (after written and untracked, changes are
        committed and then an activity record is created with another commit). The last commit can be used in a
        different branch where objects were written, but can't contain any objects to push in the current branch.

        Args:
            commit_hash(str): Commit hash to check if in branch

        Returns:
            bool
        """
        try:
            subprocess.run(['git', 'merge-base', '--is-ancestor', commit_hash, 'HEAD~1'], check=True,
                           cwd=self.dataset.root_dir)
            return True
        except subprocess.CalledProcessError:
            return False

    def objects_to_push(self, remove_duplicates: bool = False) -> List[PushObject]:
        """Return a list of named tuples of all objects that need to be pushed

        Returns:
            List[namedtuple]
        """
        objects = list()
        if os.path.exists(self.push_dir):
            push_files = [f for f in os.listdir(self.push_dir) if os.path.isfile(os.path.join(self.push_dir, f))]

            if push_files:
                object_ids: List[str] = list()
                for pf in push_files:
                    if os.path.basename(pf) == '.DS_Store':
                        continue

                    if not self._commit_in_branch(pf):
                        continue

                    with open(os.path.join(self.push_dir, pf), 'rt') as pfh:
                        lines = pfh.readlines()
                        lines = sorted(lines)
                        for line in lines:
                            line = line.strip()
                            dataset_path, object_path = line.split(',')
                            _, object_id = object_path.rsplit('/', 1)

                            # Handle de-duplicating objects if the backend supports it
                            if remove_duplicates is True:
                                if object_id in object_ids:
                                    continue

                                object_ids.append(object_id)

                            objects.append(PushObject(dataset_path=dataset_path, object_path=object_path, revision=pf))

            objects = natsorted(objects, key=attrgetter('dataset_path'))

        return objects

    def num_objects_to_push(self, remove_duplicates: bool = False) -> int:
        """Helper to get the total number of objects to push

        Returns:
            int
        """
        return len(self.objects_to_push(remove_duplicates))

    def push_objects(self, objs: List[PushObject], progress_update_fn: Callable) -> PushResult:
        """Method to push the provided objects

        This method hands most of the work over to the StorageBackend implementation for the dataset. It is expected
        that the StorageBackend will return a PushResult named tuple so the user can be properly notified and
        everything stays consistent.

        Args:
            objs: list of PushObjects, detailing the objects to push to the backend
            progress_update_fn: A callable with arg "completed_bytes" (int) indicating how many bytes have been
                                uploaded in since last called

        Returns:
            IOResult
        """
        if isinstance(self, UnmanagedStorageBackend):
            raise TypeError("Cannot push objects using an Unmanaged dataset storage type")

        try:
            self.dataset.backend.prepare_push(self.dataset, objs)  # type: ignore
            result = self.dataset.backend.push_objects(self.dataset, objs, progress_update_fn)  # type: ignore
            self.dataset.backend.finalize_push(self.dataset)  # type: ignore
        except Exception as err:
            logger.exception(err)
            raise

        return result

    def _gen_pull_objects(self, keys: List[str]) -> List[PullObject]:
        """

        Args:
            keys:

        Returns:

        """
        result = list()
        revision = self.manifest.dataset_revision
        for key in keys:
            data = self.manifest.dataset_to_object_path(key)
            result.append(PullObject(object_path=data, revision=revision, dataset_path=key))

        return result

    def pull_objects(self, keys: List[str], progress_update_fn: Callable, link_revision: bool = True) -> PullResult:
        """Method to pull a single object

        This method hands most of the work over to the StorageBackend implementation for the dataset. It is expected
        that the StorageBackend will return a PushResult named tuple so the user can be properly notified and
        everything stays consistent.

        Args:
            keys: list of keys (relative paths) to pull
            progress_update_fn: A callable with arg "completed_bytes" (int) indicating how many bytes have been
                                downloaded in since last called
            link_revision: flag indicating if you should link the files. Typically true, but useful to be false when
                           multiple processes are downloading files (e.g. the `pull_objects` background job).

        Returns:
            PullResult
        """
        objs: List[PullObject] = self._gen_pull_objects(keys)

        # Pull the object
        self.dataset.backend.prepare_pull(self.dataset, objs)
        result = self.dataset.backend.pull_objects(self.dataset, objs, progress_update_fn)
        self.dataset.backend.finalize_pull(self.dataset)

        # Relink the revision
        if link_revision:
            self.manifest.link_revision()

        # Return pull result
        return result

    def _get_pull_all_keys(self) -> List[str]:
        """Helper to get all keys for files that need to be downloaded, ignoring files that already exist and
        linking files if needed

        Returns:
            list
        """
        keys_to_pull = list()
        for key in self.manifest.manifest:
            # If dir, skip
            if key[-1] == os.path.sep:
                continue

            # If object is linked to the revision already, skip
            revision_path = os.path.join(self.manifest.current_revision_dir, key)
            if os.path.exists(revision_path):
                continue

            # Check if file exists in object cache and simply needs to be linked
            obj_path = self.manifest.dataset_to_object_path(key)
            if os.path.isfile(obj_path):
                os.link(obj_path, revision_path)
                continue

            # Queue for downloading
            keys_to_pull.append(key)

        return keys_to_pull

    def compute_pull_batches(self, keys: Optional[List[str]] = None,
                             pull_all: Optional[bool] = False) -> Tuple[List[List[str]], int, int]:
        """Method to compute object pull batches that attempt to spread io across available cores

        Args:
            keys: List of keys to download (relative file paths)
            pull_all: Optional flag, if True, will download all remaining files in the dataset

        Returns:
            list, int
        """
        if not keys and not pull_all:
            raise ValueError("Either `keys` must be provided or `pull_all` set to True for batch computation.")

        if pull_all:
            keys = self._get_pull_all_keys()

        num_cores = self.dataset.client_config.download_cpu_limit
        key_batches: List[List] = [list() for _ in range(num_cores)]
        size_sums = [0 for _ in range(num_cores)]

        # Build batches by dividing keys across batches by file size
        if keys:
            for key in keys:
                data = self.manifest.get(key)
                index = size_sums.index(min(size_sums))
                key_batches[index].append(key)
                file_size = int(data['size'])
                size_sums[index] += file_size

        # Prune Jobs back if there are lots of cores but not lots of work
        key_batches = [x for x in key_batches if x != []]

        return key_batches, sum(size_sums), (len(keys) if keys else 0)

    def compute_push_batches(self) -> Tuple[List[List[PushObject]], int, int]:
        """Method to compute object push batches that attempt to spread io across available cores

        Returns:
            list, int, int, int
        """
        num_cores = self.dataset.client_config.upload_cpu_limit
        obj_batches: List[List] = [list() for _ in range(num_cores)]
        size_sums = [0 for _ in range(num_cores)]

        should_dedup = self.dataset.backend.client_should_dedup_on_push  # type: ignore
        objs: List[PushObject] = self.objects_to_push(remove_duplicates=should_dedup)

        # Build batches by dividing keys across batches by file size
        for obj in objs:
            index = size_sums.index(min(size_sums))
            obj_batches[index].append(obj)
            file_size = os.path.getsize(obj.object_path)
            size_sums[index] += file_size

        # Prune Jobs back if there are lots of cores but not lots of work
        obj_batches = [x for x in obj_batches if x != []]

        return obj_batches, sum(size_sums), len(objs)
