import os
import shutil
import uuid
import datetime
from natsort import natsorted
from pkg_resources import resource_filename
import pathlib
import subprocess
import glob

from typing import Any, NamedTuple, Optional, Callable, List, Tuple, Dict

from gtmcore.exceptions import GigantumException
from gtmcore.labbook.schemas import CURRENT_SCHEMA as LABBOOK_CURRENT_SCHEMA
from gtmcore.dataset.schemas import CURRENT_SCHEMA as DATASET_CURRENT_SCHEMA
from gtmcore.gitlib import GitAuthor, RepoLocation
from gtmcore.logging import LMLogger
from gtmcore.configuration import Configuration
from gtmcore.configuration.utils import call_subprocess
from gtmcore.labbook import SecretStore
from gtmcore.labbook.labbook import LabBook
from gtmcore.dataset.dataset import Dataset
from gtmcore.inventory import Repository
from gtmcore.dataset import storage
from gtmcore.activity import ActivityStore, ActivityDetailRecord, ActivityDetailType, ActivityRecord, ActivityType, \
    ActivityAction
from gtmcore.activity.utils import ImmutableList, DetailRecordList, TextData
from gtmcore.dataset import Manifest


logger = LMLogger.get_logger()


class InventoryException(GigantumException):
    pass


# Named tuple for Dataset cleanup jobs that need to be scheduled
DatasetCleanupJob = NamedTuple('DatasetCleanupJob', [('namespace', str), ('name', str), ('cache_root', str)])


class InventoryManager(object):
    """ This class absorbs the complexity of accepting data structures into the client's
        working directory. We need this class because interacting with the "inventory"
        (i.e., the tree of labbooks located in the user's working directory) can be
        a messy and error-prone process. Any other functionality that needs to insert
        data into the inventory no longer needs to be aware of any specifics of the internal
        structure of it or worry about cleanup. """

    def __init__(self, config_file: Optional[str] = None) -> None:
        self.config_file = config_file
        cfg = Configuration(self.config_file)
        self.inventory_root = os.path.expanduser(cfg.config['git']['working_directory'])

    def __str__(self) -> str:
        return f'<InventoryManager: {self.inventory_root}>'

    def __eq__(self, other) -> bool:
        return isinstance(other, InventoryManager) \
               and self.inventory_root == other.inventory_root

    # TODO 1069 - this is somewhat redundant with the owner property on labbook (and probably dataset?). Standardize.
    @staticmethod
    def query_owner(repository: Repository) -> str:
        """Returns the Repository's owner in the Inventory. """
        tokens = repository.root_dir.rsplit('/', 3)
        # expected pattern: gigantum/<username>/<owner>/<labbook or dataset>/<project or dataset name>
        if len(tokens) < 3 or tokens[-2] not in ['labbooks', 'datasets']:
            raise InventoryException(f'Unexpected root in {str(repository)}')
        return tokens[-3]

    @staticmethod
    def query_owner_of_linked_dataset(dataset: Dataset) -> str:
        """Returns the Dataset's owner when embedded in a Project repository. """
        tokens = dataset.root_dir.rsplit('/', 3)
        # expected pattern: <Project root>/.gigantum/datasets/<owner>/<dataset name>
        if len(tokens) < 4 or tokens[-3] != 'datasets':
            raise InventoryException(f'Unexpected root in {str(dataset)}')
        return tokens[-2]

    def repository_exists(self, username: str, owner: str, repository_name: str) -> bool:
        """Method indicating if a repository (project or dataset) exists locally

        Args:
            username: currently logged in user
            owner: the owner of the project/dataset
            repository_name: the name of the project/dataset

        Returns:
            bool
        """
        # Check if Project exists locally
        labbooks = self.list_repository_ids(username, 'labbook')
        for l in labbooks:
            if l[1] == owner and l[2] == repository_name:
                return True

        # Check if Dataset exists locally
        datasets = self.list_repository_ids(username, 'dataset')
        for d in datasets:
            if d[1] == owner and d[2] == repository_name:
                return True

        return False

    def _put_labbook(self, path: str, username: str, owner: str) -> LabBook:
        # Validate that given path contains labbook
        temp_lb = self.load_labbook_from_directory(path)

        p = os.path.join(self.inventory_root, username, owner, 'labbooks')
        dname = os.path.basename(path)

        if not os.path.exists(p):
            os.makedirs(p, exist_ok=True)

        if os.path.exists(os.path.join(p, dname)):
            raise InventoryException(f"Project directory {dname} already exists")

        final_path = shutil.move(path, p)
        assert os.path.dirname(final_path) != 'labbooks', \
               f"shutil.move used incorrectly"

        lb = self.load_labbook_from_directory(final_path)
        return lb

    def put_labbook(self, path: str, username: str, owner: str) -> LabBook:
        """ Take given path to a candidate labbook and insert it
        into its proper place in the file system.

        Args:
            path: Path to a given labbook
            username: Active username
            owner: Intended owner of labbook

        Returns:
            LabBook
        """
        try:
            lb = self._put_labbook(path, username, owner)

            return lb
        except Exception as e:
            logger.error(e)
            raise InventoryException(e)

    def load_labbook_from_directory(self, path: str, author: Optional[GitAuthor] = None) -> LabBook:
        """ Load and return a LabBook object from a given path on disk

        Warning - Deprecated !! Use load_labbook instead

        Args:
            path: Full path on disk to LabBook
            author: Labbook Author of commits

        Returns:
            LabBook object
        """
        try:
            lb = LabBook(config_file=self.config_file)
            lb._set_root_dir(path)
            lb._load_gigantum_data()
            lb._validate_gigantum_data()
            lb.author = author
            return lb
        except Exception as e:
            logger.error(e)
            raise InventoryException(e)

    def load_labbook(self, username: str, owner: str, labbook_name: str,
                     author: Optional[GitAuthor] = None) -> LabBook:
        try:
            lb = LabBook(self.config_file)
            lbroot = os.path.join(self.inventory_root, username,
                                  owner, 'labbooks', labbook_name)
            lb._set_root_dir(lbroot)
            lb._load_gigantum_data()
            lb._validate_gigantum_data()
            lb.author = author
            return lb
        except Exception as e:
            raise InventoryException(f"Cannot retrieve "
                                     f"({username}, {owner}, {labbook_name}): {e}")

    def list_repository_ids(self, username: str, repository_type: str) -> List[Tuple[str, str, str]]:
        """Return a list of (username, owner, labbook or dataset name) tuples corresponding
           to all repositories (labbook or datasets) whose existence is inferred. Since this method does not
           actually load the repositories, it returns quite fast.

           Warnings - there *may* exist corrupted repositories in the returned set -
            no validation is guaranteed.

        Args:
            username(str): Active username to crawl for
            repository_type(str): type of repository to list (labbook or dataset)

        Returns:
            List of 3-tuples containing (username, owner, labbook-name)
        """
        if repository_type not in ["labbook", "dataset"]:
            raise ValueError(f"Unsupported repository type: {repository_type}")

        user_root = os.path.join(self.inventory_root, username)
        if not os.path.exists(user_root):
            return []

        owner_dirs = sorted([os.path.join(user_root, d)
                             for d in os.listdir(user_root)
                             if os.path.isdir(os.path.join(user_root, d))])
        repository_paths = []
        for owner_dir in owner_dirs:
            if not os.path.isdir(os.path.join(owner_dir, f'{repository_type}s')):
                continue
            repository_dirs = sorted([os.path.join(owner_dir, f'{repository_type}s', l)
                                      for l in os.listdir(os.path.join(owner_dir, f'{repository_type}s'))
                                      if os.path.isdir(os.path.join(owner_dir, f'{repository_type}s', l))])
            for repository_dir in repository_dirs:
                git_dir = os.path.join(repository_dir, '.git')
                gtm_dir = os.path.join(repository_dir, '.gigantum')
                if os.path.isdir(git_dir) and os.path.isdir(gtm_dir):
                    repository_paths.append((username,
                                             os.path.basename(owner_dir),
                                             os.path.basename(repository_dir)))
                else:
                    logger.warning(f'Unknown artifact in inventory: {repository_dir}')
        return repository_paths

    def list_labbooks(self, username: str, sort_mode: Optional[str] = "name") -> List[LabBook]:
        """ Return list of all available labbooks for a given user

        Args:
            username: Active username
            sort_mode: Sort by name, creation date, or last modified date.

        Returns:
            Sorted list of LabBook objects
        """
        local_labbooks = []
        for username, owner, lbname in self.list_repository_ids(username, 'labbook'):
            try:
                labbook = self.load_labbook(username, owner, lbname)
                local_labbooks.append(labbook)
            except Exception as e:
                logger.error(e)

        if sort_mode == "name":
            return natsorted(local_labbooks, key=lambda ds: ds.name)
        elif sort_mode == 'modified_on':
            return sorted(local_labbooks, key=lambda ds: ds.modified_on)
        elif sort_mode == 'created_on':
            return sorted(local_labbooks, key=lambda ds: ds.creation_date)
        else:
            raise InventoryException(f"Invalid sort mode {sort_mode}")

    def _safe_load(self, username, key_f: Callable) -> List[Tuple[LabBook, Any]]:
        """Helper method to prevent loading corrupt LabBooks into the list of local labbooks."""
        local_labbooks = []
        for username, owner, lbname in self.list_repository_ids(username, 'labbook'):
            try:
                labbook = self.load_labbook(username, owner, lbname)
                key = key_f(labbook)
                local_labbooks.append((labbook, key))
            except Exception as e:
                logger.error(e)
        return local_labbooks

    def create_labbook_disabled_lfs(self, username: str, owner: str, labbook_name: str,
                                    description: Optional[str] = None,
                                    author: Optional[GitAuthor] = None) -> LabBook:
        path = self._new_labbook(username=username, owner={'username': owner},
                                 name=labbook_name, description=description,
                                 author=author, bypass_lfs=True)
        lb = self.load_labbook_from_directory(path, author=author)
        return lb

    def create_labbook(self, username: str, owner: str, labbook_name: str,
                       description: Optional[str] = None, author: Optional[GitAuthor] = None) -> LabBook:
        """Create a new LabBook in this Gigantum working directory.

        Args:
            username: Active username
            owner: Namespace in which to place this LabBook
            labbook_name: Name of labbook
            description: Optional brief description of LabBook
            author: Optional Git Author

        Returns:
            Newly created LabBook instance

        """
        path = self._new_labbook(username=username, owner={'username': owner},
                                 name=labbook_name, description=description,
                                 author=author, bypass_lfs=False)
        return self.load_labbook_from_directory(path, author=author)

    def _new_labbook(self, owner: Dict[str, str], name: str,
                     username: str,
                     description: Optional[str] = None,
                     bypass_lfs: bool = False,
                     author: Optional[GitAuthor] = None) -> str:
        """Method to create a new minimal LabBook instance on disk

        NOTE: This is the exact same as the old LabBook.new() method.
        This method is deprecated and will be re-worked in the near future.

        Args:
            owner(dict): Owner information. Can be a user or a team/org.
            name(str): Name of the LabBook
            username(str): Username of the logged in user. Used to store the LabBook in the proper location. If omitted
                           the owner username is used
            description(str): A short description of the LabBook
            bypass_lfs: If True does not use LFS to track input and output dirs.
            author: Git author for commits

        Returns:
            str: Path to the LabBook contents
        """

        if not username:
            logger.warning("Using owner username `{}` when making new labbook".format(owner['username']))
            username = owner["username"]

        labbook = LabBook(config_file=self.config_file, author=author)

        # Build data file contents
        buildinfo = Configuration(self.config_file).config['build_info']
        labbook._data = {
            "schema": LABBOOK_CURRENT_SCHEMA,
            "id": uuid.uuid4().hex,
            "name": name,
            "description": description or '',
            "build_info": buildinfo,
            "created_on": str(datetime.datetime.utcnow().isoformat())
        }

        labbook._validate_gigantum_data()

        logger.info("Creating new labbook on disk for {}/{}/{} ...".format(username, owner, name))

        # lock while creating initial directory
        with labbook.lock(lock_key=f"new_labbook_lock|{username}|{owner['username']}|{name}"):
            # Verify or Create user subdirectory
            # Make sure you expand a user dir string
            starting_dir = os.path.expanduser(labbook.client_config.config["git"]["working_directory"])
            user_dir = os.path.join(starting_dir, username)
            if not os.path.isdir(user_dir):
                os.makedirs(user_dir)

            # Create owner dir - store LabBooks in working dir > logged in user > owner
            owner_dir = os.path.join(user_dir, owner["username"])
            if not os.path.isdir(owner_dir):
                os.makedirs(owner_dir)

                # Create `labbooks` subdir in the owner dir
                owner_dir = os.path.join(owner_dir, "labbooks")
            else:
                owner_dir = os.path.join(owner_dir, "labbooks")

            # Verify name not already in use
            if os.path.isdir(os.path.join(owner_dir, name)):
                raise ValueError(f"LabBook `{name}` already exists locally. Choose a new LabBook name")

            # Create LabBook subdirectory
            new_root_dir = os.path.join(owner_dir, name)
            os.makedirs(new_root_dir)
            labbook._set_root_dir(new_root_dir)

            # Init repository
            labbook.git.initialize()

            # Setup LFS
            if labbook.client_config.config["git"]["lfs_enabled"] and not bypass_lfs:
                # Make sure LFS install is setup and rack input and output directories
                call_subprocess(["git", "lfs", "install"], cwd=new_root_dir)
                call_subprocess(["git", "lfs", "track", "input/**"], cwd=new_root_dir)
                call_subprocess(["git", "lfs", "track", "output/**"], cwd=new_root_dir)

                # Commit .gitattributes file
                labbook.git.add(os.path.join(labbook.root_dir, ".gitattributes"))
                labbook.git.commit("Configuring LFS")

            # Create Directory Structure
            dirs = [
                'code', 'input', 'output', 'output/untracked', '.gigantum',
                os.path.join('.gigantum', 'env'),
                os.path.join('.gigantum', 'env', 'base'),
                os.path.join('.gigantum', 'env', 'custom'),
                os.path.join('.gigantum', 'env', 'package_manager'),
                os.path.join('.gigantum', 'activity'),
                os.path.join('.gigantum', 'activity', 'log'),
                os.path.join('.gigantum', 'activity', 'index'),
                os.path.join('.gigantum', 'activity', 'importance'),
            ]

            for d in dirs:
                p = os.path.join(labbook.root_dir, d, '.gitkeep')
                os.makedirs(os.path.dirname(p), exist_ok=True)
                with open(p, 'w') as gk:
                    gk.write("This file is necessary to keep this directory tracked by Git"
                             " and archivable by compression tools. Do not delete or modify!")

            labbook._save_gigantum_data()
            # Create .gitignore default file
            shutil.copyfile(os.path.join(resource_filename('gtmcore', 'labbook'), 'gitignore.default'),
                            os.path.join(labbook.root_dir, ".gitignore"))

            labbook.git.add_all()

            # NOTE: this string is used to indicate there are no more activity records to get. Changing the string will
            # break activity paging.
            # TODO: Improve method for detecting the first activity record
            labbook.git.commit(f"Creating new empty LabBook: {name}")

            return labbook.root_dir

    def delete_labbook(self, username: str, owner: str, labbook_name: str) -> List[DatasetCleanupJob]:
        """Delete a Labbook from this Gigantum working directory.

        Args:
            username: Active username
            owner: Namespace of the Labbook
            labbook_name: Name of the Labbook

        Returns:
            None

        """
        lb = self.load_labbook(username, owner, labbook_name)
        target_dir = lb.root_dir

        # Get list of datasets and cache roots to schedule for cleanup
        datasets = self.get_linked_datasets(lb)
        datasets_to_schedule = list()
        for ds in datasets:
            try:
                m = Manifest(ds, username)
                if not ds.namespace:
                    raise ValueError("Dataset namespace required to schedule for cleanup")
                datasets_to_schedule.append(DatasetCleanupJob(namespace=ds.namespace,
                                                              name=ds.name,
                                                              cache_root=m.cache_mgr.cache_root))
            except Exception as err:
                # Skip errors
                logger.warning(f"Error occurred and ignored while processing submodules during Project delete: {err}")
                continue

        # Delete all secrets pertaining to this project.
        SecretStore(lb, username).clear_files()

        if 'WINDOWS_HOST' in os.environ:
            # Windows host. Remove all git clients so no file handles prevent deletion
            lb.git.repo.__del__()
            lb = None  # type: ignore

        # Remove labbook contents
        shutil.rmtree(target_dir, ignore_errors=True)

        return datasets_to_schedule

    def create_dataset(self, username: str, owner: str, dataset_name: str, storage_type: str,
                       description: Optional[str] = None, author: Optional[GitAuthor] = None) -> Dataset:
        """Create a new Dataset in this Gigantum working directory.

        Args:
            username: Active username
            owner: Namespace in which to place this Dataset
            dataset_name: Name of the Dataset
            storage_type: String identifying the type of Dataset to instantiate
            description: Optional brief description of Dataset
            author: Optional Git Author

        Returns:
            Newly created LabBook instance

        """
        dataset = Dataset(config_file=self.config_file, author=author, namespace=owner)

        if storage_type not in storage.SUPPORTED_STORAGE_BACKENDS:
            raise ValueError(f"Unsupported Dataset storage type: {storage_type}")

        try:
            build_info = Configuration(self.config_file).config['build_info']
        except KeyError:
            logger.warning("Could not obtain build_info from config")
            build_info = None

        # Build data file contents
        dataset._data = {
            "schema": DATASET_CURRENT_SCHEMA,
            "id": uuid.uuid4().hex,
            "name": dataset_name,
            "storage_type": storage_type,
            "description": description or '',
            "created_on": datetime.datetime.utcnow().isoformat(),
            "build_info": build_info
        }
        dataset._validate_gigantum_data()

        logger.info("Creating new Dataset on disk for {}/{}/{}".format(username, owner, dataset_name))
        # lock while creating initial directory
        with dataset.lock(lock_key=f"new_dataset_lock|{username}|{owner}|{dataset_name}"):
            # Verify or Create user subdirectory
            # Make sure you expand a user dir string
            starting_dir = os.path.expanduser(dataset.client_config.config["git"]["working_directory"])
            user_dir = os.path.join(starting_dir, username)
            if not os.path.isdir(user_dir):
                os.makedirs(user_dir)

            # Create owner dir - store LabBooks in working dir > logged in user > owner
            owner_dir = os.path.join(user_dir, owner)
            if not os.path.isdir(owner_dir):
                os.makedirs(owner_dir)

                # Create `datasets` subdir in the owner dir
                owner_dir = os.path.join(owner_dir, "datasets")
            else:
                owner_dir = os.path.join(owner_dir, "datasets")

            # Verify name not already in use
            if os.path.isdir(os.path.join(owner_dir, dataset_name)):
                raise ValueError(f"Dataset `{dataset_name}` already exists locally. Choose a new Dataset name")

            # Create Dataset subdirectory
            new_root_dir = os.path.join(owner_dir, dataset_name)
            os.makedirs(new_root_dir)
            dataset._set_root_dir(new_root_dir)

            # Init repository
            dataset.git.initialize()

            # Create Directory Structure
            dirs = [
                'manifest', 'metadata', '.gigantum',
                os.path.join('.gigantum', 'activity'),
                os.path.join('.gigantum', 'activity', 'log')
            ]

            # Create .gitignore default file
            shutil.copyfile(os.path.join(resource_filename('gtmcore', 'dataset'), 'gitignore.default'),
                            os.path.join(dataset.root_dir, ".gitignore"))

            for d in dirs:
                p = os.path.join(dataset.root_dir, d, '.gitkeep')
                os.makedirs(os.path.dirname(p), exist_ok=True)
                with open(p, 'w') as gk:
                    gk.write("This file is necessary to keep this directory tracked by Git"
                             " and archivable by compression tools. Do not delete or modify!")

            dataset._save_gigantum_data()

            # Create an empty storage.json file
            dataset.backend_config = {}

            # Commit
            dataset.git.add_all()

            # NOTE: this string is used to indicate there are no more activity records to get. Changing the string will
            # break activity paging.
            # TODO: Improve method for detecting the first activity record
            dataset.git.commit(f"Creating new empty Dataset: {dataset_name}")

            # Create Activity Record
            adr = ActivityDetailRecord(ActivityDetailType.DATASET,
                                       show=False,
                                       importance=0,
                                       data=TextData('plain', f"Created new Dataset: {username}/{dataset_name}"))

            ar = ActivityRecord(ActivityType.DATASET,
                                message=f"Created new Dataset: {username}/{dataset_name}",
                                show=True,
                                importance=255,
                                linked_commit=dataset.git.commit_hash,
                                detail_objects=DetailRecordList([adr]))

            store = ActivityStore(dataset)
            store.create_activity_record(ar)

            # Initialize file cache and link revision
            m = Manifest(dataset, username)
            m.link_revision()

            return dataset

    def delete_dataset(self, username: str, owner: str, dataset_name: str) -> DatasetCleanupJob:
        """Delete a Dataset from this Gigantum working directory.

        Args:
            username: Active username
            owner: Namespace in which to place this Dataset
            dataset_name: Name of the Datasets

        Returns:
            None

        """
        ds = self.load_dataset(username, owner, dataset_name)
        target_dir = ds.root_dir

        # Delete dataset contents from file cache
        m = Manifest(ds, username)
        cache_root = m.cache_mgr.cache_root
        m = None  # type: ignore

        if 'WINDOWS_HOST' in os.environ:
            # Windows host. Remove all git clients so no file handles prevent deletion
            ds.git.repo.__del__()
            ds = None  # type: ignore

        # Delete dataset repository from working dir
        shutil.rmtree(target_dir, ignore_errors=True)

        return DatasetCleanupJob(namespace=owner,
                                 name=dataset_name,
                                 cache_root=cache_root)

    def put_dataset(self, path: str, username: str, owner: str) -> Dataset:
        try:
            return self._put_dataset(path, username, owner)
        except Exception as e:
            logger.exception(e)
            raise InventoryException(e)

    def _put_dataset(self, path: str, username: str, owner: str) -> Dataset:
        # Validate that given path contains a dataset
        _ = self.load_dataset_from_directory(path)

        p = os.path.join(self.inventory_root, username, owner, 'datasets')
        dir_name = os.path.basename(path)
        if os.path.exists(p) and dir_name in os.listdir(p):
            raise InventoryException(f"Dataset directory {dir_name} already exists")

        if not os.path.exists(p):
            os.makedirs(p, exist_ok=True)

        if os.path.exists(os.path.join(p, dir_name)):
            raise InventoryException(f"Dataset directory {dir_name} already exists")

        final_path = shutil.move(path, p)
        assert os.path.dirname(final_path) != 'datasets', f"shutil.move used incorrectly"

        ds = self.load_dataset_from_directory(final_path)

        # link dataset objects
        ds.namespace = owner
        m = Manifest(ds, logged_in_username=username)
        m.link_revision()

        return ds

    def load_dataset(self, username: str, owner: str, dataset_name: str,
                     author: Optional[GitAuthor] = None) -> Dataset:
        """Method to load a dataset from disk

        Args:
            username(str): Username of user logged in
            owner(str): Username of the owner (namespace) of the Dataset
            dataset_name(str): Name of the dataset
            author(GitAuthor): GitAuthor object

        Returns:
            Dataset
        """
        try:
            ds = Dataset(self.config_file, author=author, namespace=owner)

            ds_root = os.path.join(self.inventory_root, username,
                                   owner, 'datasets', dataset_name)
            ds._set_root_dir(ds_root)
            ds._load_gigantum_data()
            ds._validate_gigantum_data()
            return ds
        except Exception as e:
            raise InventoryException(f"Cannot retrieve ({username}, {owner}, {dataset_name}): {e}")

    def load_dataset_from_directory(self, path: str, author: Optional[GitAuthor] = None) -> Dataset:
        """ Load a Dataset temporarily from an arbitrary directory.

        Args:
            path: Path to candidate dataset - generally somewhere in /tmp
            author: Optional GitAuthor

        Returns:
            Dataset object
        """
        try:
            ds = Dataset(config_file=self.config_file)
            ds._set_root_dir(path)
            ds._load_gigantum_data()
            ds._validate_gigantum_data()
            ds.author = author
            return ds
        except Exception as e:
            logger.error(e)
            raise InventoryException(e)

    def list_datasets(self, username: str, sort_mode: str = "name") -> List[Dataset]:
        """ Return list of all available datasets for a given user

        This will result in sorting a-z and with the oldest to newest.

        Args:
            username: Active username
            sort_mode: One of "name", "modified_on" or "created_on"

        Returns:
            Sorted list of Dataset objects
        """
        local_datasets = []
        for username, owner, dsname in self.list_repository_ids(username, 'dataset'):
            try:
                dataset = self.load_dataset(username, owner, dsname)
                local_datasets.append(dataset)
            except Exception as e:
                logger.error(e)

        if sort_mode == "name":
            return natsorted(local_datasets, key=lambda ds: ds.name)
        elif sort_mode == 'modified_on':
            return sorted(local_datasets, key=lambda ds: ds.modified_on)
        elif sort_mode == 'created_on':
            return sorted(local_datasets, key=lambda ds: ds.creation_date)
        else:
            raise InventoryException(f"Invalid sort mode {sort_mode}")

    def link_dataset_to_labbook(self, dataset_url: str, dataset_namespace: str, dataset_name: str,
                                labbook: LabBook, username: str) -> Dataset:
        """

        Args:
            dataset_url:
            dataset_namespace:
            dataset_name:
            labbook:

        Returns:

        """
        def _clean_submodule():
            """Helper method to clean a submodule reference from a repository"""
            if os.path.exists(absolute_submodule_dir):
                logger.warning(f"Cleaning {relative_submodule_dir} from parent git repo")
                try:
                    call_subprocess(['git', 'rm', '-f', '--cached', relative_submodule_dir], cwd=labbook.root_dir)
                except subprocess.CalledProcessError:
                    logger.warning(f"git rm on {relative_submodule_dir} failed. Continuing...")
                    pass

            if os.path.exists(absolute_submodule_dir):
                logger.warning(f"Removing {absolute_submodule_dir} directory")
                shutil.rmtree(absolute_submodule_dir)

            if os.path.exists(git_module_dir):
                logger.warning(f"Removing {git_module_dir} directory")
                shutil.rmtree(git_module_dir)

        relative_submodule_dir = os.path.join('.gigantum', 'datasets', dataset_namespace, dataset_name)
        absolute_submodule_dir = os.path.join(labbook.root_dir, relative_submodule_dir)
        absolute_submodule_root = os.path.join(labbook.root_dir, '.gigantum', 'datasets', dataset_namespace)
        git_module_dir = os.path.join(labbook.root_dir, '.git', 'modules', f"{dataset_namespace}&{dataset_name}")

        if not os.path.exists(absolute_submodule_root):
            pathlib.Path(absolute_submodule_root).mkdir(parents=True, exist_ok=True)

        if os.path.exists(absolute_submodule_dir) and os.path.exists(git_module_dir):
            # Seem to be trying to link a dataset after a reset removed the dataset. Clean up first.
            _clean_submodule()

        # This URL will end up including the username in .gitmodules, we remove that below
        remote = RepoLocation(dataset_url, current_username=username)
        try:
            # Link dataset via submodule reference
            call_subprocess(['git', 'submodule', 'add', '--name', f"{dataset_namespace}&{dataset_name}", remote.remote_location,
                            relative_submodule_dir], cwd=labbook.root_dir)

        except subprocess.CalledProcessError:
            logger.warning("Failed to link dataset. Attempting to repair repository and link again.")
            _clean_submodule()

            # Try to add again 1 more time, allowing a failure to raise an exception
            call_subprocess(['git', 'submodule', 'add', '--name', f"{dataset_namespace}&{dataset_name}", remote.remote_location,
                            relative_submodule_dir], cwd=labbook.root_dir)

            # If you got here, repair worked and link OK
            logger.info("Repository repair and linking retry successful.")

        # Remove username from .gitmodules
        anon_remote = RepoLocation(dataset_url, current_username=None)
        call_subprocess(['git', 'config', '--file=.gitmodules', f"submodule.{dataset_namespace}&{dataset_name}.url",
                         anon_remote.remote_location], cwd=labbook.root_dir)

        labbook.git.add_all()
        commit = labbook.git.commit(f"adding submodule ref to link dataset {dataset_namespace}/{dataset_name}")

        ds = self.load_dataset_from_directory(absolute_submodule_dir)
        dataset_revision = ds.git.repo.head.commit.hexsha

        # Add Activity Record
        adr = ActivityDetailRecord(ActivityDetailType.DATASET,
                                   show=False,
                                   action=ActivityAction.CREATE,
                                   data=TextData('markdown', f"Linked Dataset `{dataset_namespace}/{dataset_name}` to "
                                                             f"project at revision `{dataset_revision}`"))

        ar = ActivityRecord(ActivityType.DATASET,
                            message=f"Linked Dataset {dataset_namespace}/{dataset_name} to project.",
                            linked_commit=commit.hexsha,
                            tags=ImmutableList(["dataset"]),
                            show=True,
                            detail_objects=DetailRecordList([adr]))

        ars = ActivityStore(labbook)
        ars.create_activity_record(ar)

        return ds

    def unlink_dataset_from_labbook(self, dataset_namespace: str, dataset_name: str, labbook: LabBook) -> None:
        """Method to removed a dataset reference from a labbook

        Args:
            dataset_namespace:
            dataset_name:
            labbook:

        Returns:

        """
        submodule_dir = os.path.join('.gigantum', 'datasets', dataset_namespace, dataset_name)
        call_subprocess(['git', 'rm', '-f', submodule_dir], cwd=labbook.root_dir)

        git_module_dir = os.path.join(labbook.root_dir, '.git', 'modules', f"{dataset_namespace}&{dataset_name}")
        if os.path.exists(git_module_dir):
            shutil.rmtree(git_module_dir)

        absolute_submodule_dir = os.path.join(labbook.root_dir, '.gigantum', 'datasets', dataset_namespace,
                                              dataset_name)
        if os.path.exists(absolute_submodule_dir):
            shutil.rmtree(absolute_submodule_dir)

        labbook.git.add_all()
        commit = labbook.git.commit("removing submodule ref")

        # Add Activity Record
        adr = ActivityDetailRecord(ActivityDetailType.DATASET,
                                  show=False,
                                  action=ActivityAction.DELETE,
                                  data=TextData('markdown', f"Unlinked Dataset `{dataset_namespace}/{dataset_name}` from project"))

        ar = ActivityRecord(ActivityType.DATASET,
                            message=f"Unlinked Dataset {dataset_namespace}/{dataset_name} from project.",
                            linked_commit=commit.hexsha,
                            tags=ImmutableList(["dataset"]),
                            show=True,
                            detail_objects=DetailRecordList([adr]))

        ars = ActivityStore(labbook)
        ars.create_activity_record(ar)

    @staticmethod
    def update_linked_datasets(labbook: LabBook, username: str) -> None:
        """Method to initialize or update all git submodule references for linked datasets.

        This is used when loading and initializing linked datasets

        Args:
            labbook: The labbook instance to inspect
            username: the current logged in username

        Returns:
            None
        """
        submodules = labbook.git.list_submodules()
        for submodule in submodules:
            try:
                namespace, dataset_name = submodule.split("&")
                rel_submodule_dir = os.path.join('.gigantum', 'datasets', namespace, dataset_name)
                submodule_dir = os.path.join(labbook.root_dir, rel_submodule_dir)

                # The following three commands may be null-ops, but they're local operations that should be very fast
                call_subprocess(['git', 'submodule', 'init', '--', rel_submodule_dir],
                                cwd=labbook.root_dir, check=True)

                # We update the URL in our .gitconfig to include the username
                # This shouldn't have a username in it, but it's OK if it does
                anon_url = call_subprocess(['git', 'config', f"submodule.{submodule}.url"],
                                           cwd=labbook.root_dir, check=True)
                user_remote = RepoLocation(anon_url.strip(), username)
                call_subprocess(['git', 'config', f"submodule.{submodule}.url", user_remote.remote_location],
                                cwd=labbook.root_dir, check=True)

                call_subprocess(['git', 'submodule', 'update', '--', rel_submodule_dir],
                                cwd=labbook.root_dir, check=True)

                ds = InventoryManager().load_dataset_from_directory(submodule_dir)
                ds.namespace = namespace
                manifest = Manifest(ds, username)
                manifest.force_reload()
                manifest.link_revision()

            except Exception as err:
                logger.warning(f"Failed to initialize linked Dataset (submodule reference): {submodule}. "
                               f"This may be an actual error or simply due to repository permissions",
                               exc_info=True)
                logger.warning(err)

        # Clean out lingering dataset files if you previously had a dataset linked, but now don't
        current_dataset_set = set([os.path.join(labbook.root_dir,
                                                '.gigantum',
                                                'datasets',
                                                x.replace("&", "/")) for x in submodules])
        dataset_directory_set = set(glob.glob(os.path.join(labbook.root_dir, '.gigantum', 'datasets', "*/*")))
        defunct_dataset_dirs = dataset_directory_set.difference(current_dataset_set)
        for submodule_dir_to_clean in defunct_dataset_dirs:
            if os.path.isdir(submodule_dir_to_clean):
                logger.info(f"Detected un-used dataset submodule dir. Removing: {submodule_dir_to_clean}")
                shutil.rmtree(submodule_dir_to_clean)

    def update_linked_dataset_reference(self, dataset_namespace: str, dataset_name: str, labbook: LabBook) -> Dataset:
        """Method to update a linked dataset reference to the latest revision

        Args:
            dataset_namespace: owner (namespace) of the dateset
            dataset_name: name of the dataset
            labbook: labbook instance to which the dataset is linked

        Returns:
            none1
        """
        # Load dataset from inside Project directory
        submodule_dir = os.path.join(labbook.root_dir, '.gigantum', 'datasets', dataset_namespace, dataset_name)
        ds = self.load_dataset_from_directory(submodule_dir, author=labbook.author)
        ds.namespace = dataset_namespace

        # Update the submodule reference with the latest changes
        original_revision = ds.git.repo.head.object.hexsha
        ds.git.fetch()

        latest_revision = call_subprocess(['git', 'rev-list', 'origin/master', '--max-count=1'],
                                          cwd=ds.root_dir, check=True)
        latest_revision = latest_revision.strip()

        # If the submodule has changed, commit the changes.
        if original_revision != latest_revision:
            call_subprocess(['git', 'checkout', '-q', latest_revision],
                            cwd=ds.root_dir, check=True)

            labbook.git.add_all()
            commit = labbook.git.commit("Updating submodule ref")

            # Add Activity Record
            adr = ActivityDetailRecord(ActivityDetailType.DATASET,
                                       show=False,
                                       action=ActivityAction.DELETE,
                                       data=TextData('markdown', f"Updated Dataset `{dataset_namespace}/{dataset_name}` link to {latest_revision}"))

            msg = f"Updated Dataset `{dataset_namespace}/{dataset_name}` link to version {latest_revision[0:8]}"
            ar = ActivityRecord(ActivityType.DATASET,
                                message=msg,
                                linked_commit=commit.hexsha,
                                tags=ImmutableList(["dataset"]),
                                show=True,
                                detail_objects=DetailRecordList([adr]))

            ars = ActivityStore(labbook)
            ars.create_activity_record(ar)

        return ds

    def get_linked_datasets(self, labbook: LabBook) -> List[Dataset]:
        """Method to get all datasets linked to a project

        Args:
            labbook(LabBook): the labbook to inspect for linked datasets

        Returns:
            list
        """
        submodules = labbook.git.list_submodules()
        datasets = list()
        for submodule in submodules:
            try:
                namespace, dataset_name = submodule.split("&")
                submodule_dir = os.path.join(labbook.root_dir, '.gigantum', 'datasets', namespace, dataset_name)
                ds = self.load_dataset_from_directory(submodule_dir, author=labbook.author)
                ds.namespace = namespace
                datasets.append(ds)
            except InventoryException:
                continue

        return datasets
