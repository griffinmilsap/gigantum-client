from typing import List, Dict, Optional, NamedTuple, TYPE_CHECKING
import pickle
import os
from enum import Enum
from collections import OrderedDict
import json
import redis
import glob
import copy
from gtmcore.logging import LMLogger

if TYPE_CHECKING:
    from gtmcore.dataset.dataset import Dataset


logger = LMLogger.get_logger()


class PersistTaskType(Enum):
    """Enumeration of persist tasks"""
    DELETE = 0
    ADD = 1
    UPDATE = 2


# NamedTuple to capture tasks to be done to persist manifest changes to disk
PersistTask = NamedTuple('PersistTask', [('relative_path', str), ('task', PersistTaskType), ('manifest_file', str)])


class ManifestJSONEncoder(json.JSONEncoder):
    """A custom json encoder to output json files that will be moderately compatible with git"""
    def encode(self, o):
        if isinstance(o, OrderedDict):
            output = [f'"{x}":{json.dumps(o[x], separators=(",", ":"))}' for x in o]
            return "{\n" + ",\n".join(output) + "\n}"

        else:
            return json.dumps(o)


class ManifestFileCache(object):
    """Class to provide a caching layer on top of a collection of Dataset manifest files

    Note: The checkout context of the underlying dataset CANNOT change while this class is instantiated. If it does,
    you need to reload the Dataset instance and reload the Manifest instance, or run Manifest.force_reload().

    """
    def __init__(self, dataset: 'Dataset', logged_in_username: Optional[str] = None) -> None:
        self.dataset = dataset
        self.logged_in_username = logged_in_username

        self.ignore_file = os.path.join(dataset.root_dir, ".gigantumignore")

        self._redis_client: Optional[redis.StrictRedis] = None
        self._manifest: OrderedDict = OrderedDict()
        self._current_checkout_id = self.dataset.checkout_id
        self._persist_queue: List[PersistTask] = list()

        # TODO: Support ignoring files
        # self.ignored = self._load_ignored()

        self._legacy_manifest_file = os.path.join(self.dataset.root_dir, 'manifest', 'manifest0')

    @property
    def redis_client(self) -> redis.StrictRedis:
        """Property to get a redis client for manifest caching

        Returns:
            redis.StrictRedis
        """
        if not self._redis_client:
            self._redis_client = redis.StrictRedis(db=1)
        return self._redis_client

    @property
    def manifest_cache_key(self) -> str:
        """Property to get the manifest cache key for this dataset instance

        Returns:
            redis.StrictRedis
        """
        key = f"DATASET-MANIFEST-CACHE|{self._current_checkout_id}"

        if self.dataset.linked_to():
            key = f"{key}|{self.dataset.linked_to()}"

        return key

    def _load_legacy_manifest(self) -> OrderedDict:
        """Method to load the manifest file

        Returns:
            dict
        """
        if os.path.exists(self._legacy_manifest_file):
            with open(self._legacy_manifest_file, 'rb') as mf:
                data = pickle.load(mf)
                # Add the filename as an attribute to allow for reverse indexing on delete
                [data[key].update(fn='manifest0') for key in data]
                return data
        else:
            return OrderedDict()

    def _write_legacy_manifest(self, data: Dict) -> None:
        """Method to write the manifest file if you've deleted or updated a value in the legacy file

        Returns:
            dict
        """
        with open(self._legacy_manifest_file, 'wb') as mf:
            pickle.dump(data, mf, pickle.HIGHEST_PROTOCOL)

    @staticmethod
    def _load_manifest_file(filename: str) -> OrderedDict:
        """Method to load a single manifest file

        Returns:
            OrderedDict
        """
        if os.path.exists(filename):
            with open(filename, 'rt') as mf:
                base_name = os.path.basename(filename)
                data = json.load(mf, object_pairs_hook=OrderedDict)
                # Add the filename as an attribute to allow for reverse indexing on delete
                [data[key].update(fn=base_name) for key in data]
                return data
        else:
            return OrderedDict()

    def _write_manifest_file(self, checkout_id: str, data: OrderedDict) -> None:
        """Method to write a manifest file to disk

        Args:
            checkout_id: the checkout id for the manifest file to write
            data: an OrderedDict containing data to write

        Returns:
            None
        """
        # Remove the reverse file index before persisting to disk
        [data[key].pop('fn', None) for key in data]

        # Pop off just the unique checkout ID
        with open(os.path.join(self.dataset.root_dir, 'manifest', f'manifest-{checkout_id}.json'), 'wt') as mf:
            json.dump(data, mf, cls=ManifestJSONEncoder)

    def _load_manifest_data(self) -> OrderedDict:
        """Method to load all manifest data, either from the memory cache or from all the manifest files

        Returns:
            OrderedDict
        """
        manifest_data = OrderedDict()
        if self.redis_client.exists(self.manifest_cache_key):
            # Load from cache
            manifest_cached_data_bytes = self.redis_client.get(self.manifest_cache_key)
            if manifest_cached_data_bytes:
                manifest_data = json.loads(manifest_cached_data_bytes.decode("utf-8"), object_pairs_hook=OrderedDict)
                self.redis_client.expire(self.manifest_cache_key, 3600)
        else:
            # Load from files
            for manifest_file in glob.glob(os.path.join(self.dataset.root_dir, 'manifest', 'manifest-*')):
                manifest_data = OrderedDict(**manifest_data, **self._load_manifest_file(manifest_file))

            # Check for legacy manifest and load if needed
            if os.path.exists(self._legacy_manifest_file):
                manifest_data = OrderedDict(**manifest_data, **self._load_legacy_manifest())

            # Cache manifest data
            if manifest_data:
                self.redis_client.set(self.manifest_cache_key, json.dumps(manifest_data, separators=(',', ':')))
                self.redis_client.expire(self.manifest_cache_key, 3600)

        return manifest_data

    def evict(self) -> None:
        """Method to remove an entry from the manifest data cache (stored in redis db 1)
        (used when needing to reload files that may still be under the same checkout context, e.g. a local
        linked dataset)

        Returns:
            None
        """
        if self.redis_client.exists(self.manifest_cache_key):
            self.redis_client.delete(self.manifest_cache_key)

        self._manifest = OrderedDict()

    def persist(self) -> None:
        """Method to persist changes to the manifest to the cache and any associated manifest file

        Returns:
            None
        """
        try:
            # Repack tasks by manifest file
            file_groups: Dict[str, List[PersistTask]] = dict()
            for task in self._persist_queue:
                if task.manifest_file in file_groups:
                    file_groups[task.manifest_file].append(task)
                else:
                    file_groups[task.manifest_file] = [task]

            # Update manifest files
            for manifest_file in file_groups:
                if manifest_file == "manifest0":
                    data = self._load_legacy_manifest()
                    for task in file_groups[manifest_file]:
                        if task.task == PersistTaskType.DELETE:
                            del data[task.relative_path]
                        else:
                            data[task.relative_path] = self._manifest[task.relative_path]

                    self._write_legacy_manifest(data)
                else:
                    full_manifest_file_path = os.path.join(self.dataset.root_dir, 'manifest', manifest_file)
                    data = self._load_manifest_file(full_manifest_file_path)
                    for task in file_groups[manifest_file]:
                        if task.task == PersistTaskType.DELETE:
                            del data[task.relative_path]
                        else:
                            data[task.relative_path] = copy.deepcopy(self._manifest[task.relative_path])
                    checkout_id = manifest_file[9:-5]  # strips off manifest- and .json from file name to get id
                    self._write_manifest_file(checkout_id, data)

            # Persist to cache
            self.redis_client.set(self.manifest_cache_key, json.dumps(self._manifest, separators=(',', ':')))
            self.redis_client.expire(self.manifest_cache_key, 3600)

        except Exception as err:
            logger.error("An error occurred while trying to persist manifest data to disk.")
            logger.exception(err)

            # Clear data so it all reloads from disk
            self._manifest = OrderedDict()
            raise IOError("An error occurred while trying to persist manifest data to disk. Refresh and try again")
        finally:
            self._persist_queue = list()

    def get_manifest(self) -> OrderedDict:
        """Method to get the current manifest

        Returns:
            OrderedDict
        """
        if not self._manifest:
            self._manifest = self._load_manifest_data()

        return self._manifest

    def add_or_update(self, relative_path: str, content_hash: str, modified_on: str, num_bytes: str) -> None:
        """Method to add or update a file in the manifest

        Note: Changes are not persisted to the disk and cache until self.persist() is called. This is done
        in manifest.py in most cases.

        Args:
            relative_path: relative path to the file
            content_hash: content hash to the file
            modified_on: modified datetime of the file
            num_bytes: number of bytes in the file

        Returns:
            None
        """
        # Make sure manifest is loaded
        self.get_manifest()

        _, checkout_id = self._current_checkout_id.rsplit('-', 1)
        if relative_path in self._manifest:
            task_type = PersistTaskType.UPDATE
            manifest_file = self._manifest[relative_path]['fn']
        else:
            task_type = PersistTaskType.ADD
            manifest_file = f'manifest-{checkout_id}.json'

        self._manifest[relative_path] = OrderedDict([('h', content_hash),
                                                     ('m', modified_on),
                                                     ('b', num_bytes),
                                                     ('fn', manifest_file)])

        self._persist_queue.append(PersistTask(relative_path=relative_path,
                                               task=task_type,
                                               manifest_file=manifest_file))

    def remove(self, relative_path: str) -> None:
        """Method to remove a file from the manifest

        Note: Changes are not persisted to the disk and cache until self.persist() is called. This is done
        in manifest.py in most cases.

        Args:
            relative_path: relative path to the file

        Returns:
            None
        """
        # Make sure manifest is loaded
        self.get_manifest()

        manifest_file = self._manifest[relative_path]['fn']
        del self._manifest[relative_path]

        self._persist_queue.append(PersistTask(relative_path=relative_path,
                                               task=PersistTaskType.DELETE,
                                               manifest_file=manifest_file))

