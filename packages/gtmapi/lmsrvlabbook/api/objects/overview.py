import base64
import graphene
import os
import glob
from collections import OrderedDict
from operator import itemgetter
from typing import List

from gtmcore.logging import LMLogger
from gtmcore.activity import ActivityStore

from lmsrvcore.auth.user import get_logged_in_username
from lmsrvcore.api.interfaces import GitRepository

from lmsrvlabbook.api.objects.activity import ActivityRecordObject
from gtmcore.dataset.manifest import Manifest

logger = LMLogger.get_logger()


class LabbookOverview(graphene.ObjectType, interfaces=(graphene.relay.Node, GitRepository)):
    """A type representing the overview of a LabBook

    It contains counts for all package managers, the last 3 activity records with show=True
    """
    # Class attribute to store package manager counts
    _package_manager_counts = None

    # Package counts
    num_apt_packages = graphene.Int()
    num_conda2_packages = graphene.Int()
    num_conda3_packages = graphene.Int()
    num_pip_packages = graphene.Int()
    num_custom_dependencies = graphene.Int()

    # last activity record that has show=True
    recent_activity = graphene.Field(ActivityRecordObject)

    # An arbitrarily long markdown document
    readme = graphene.String()

    def _get_all_package_manager_counts(self, labbook):
        """helper method to get all package manager counts in a LabBook

        Returns:
            None
        """
        pkg_dir = os.path.join(labbook.root_dir, ".gigantum", "env", "package_manager")

        self._package_manager_counts = {'apt': 0,
                                        'conda2': 0,
                                        'conda3': 0,
                                        'pip': 0}

        for f in glob.glob(os.path.join(pkg_dir, "*.yaml")):
            f = os.path.basename(f)
            mgr, _ = f.split('_', 1)

            self._package_manager_counts[mgr] = self._package_manager_counts[mgr] + 1

        return self._package_manager_counts

    @classmethod
    def get_node(cls, info, id):
        """Method to resolve the object based on it's Node ID"""
        # Parse the key
        owner, name = id.split("&")

        return LabbookOverview(owner=owner, name=name)

    def resolve_id(self, info):
        """Resolve the unique Node id for this object"""
        if not self.id:
            if not self.owner or not self.name:
                raise ValueError("Resolving a LabbookOverview Node ID requires owner and name to be set")

            self.id = f"{self.owner}&{self.name}"

        return self.id

    def resolve_num_apt_packages(self, info):
        """Resolver for getting number of apt packages in the labbook"""
        if self._package_manager_counts is None:
            return info.context.labbook_loader.load(f"{get_logged_in_username()}&{self.owner}&{self.name}").then(
                lambda labbook: self._get_all_package_manager_counts(labbook)['apt'])

        return self._package_manager_counts['apt']

    def resolve_num_conda2_packages(self, info):
        """Resolver for getting number of conda2 packages in the labbook"""
        if self._package_manager_counts is None:
            return info.context.labbook_loader.load(f"{get_logged_in_username()}&{self.owner}&{self.name}").then(
                lambda labbook: self._get_all_package_manager_counts(labbook)['conda2'])

        return self._package_manager_counts['conda2']

    def resolve_num_conda3_packages(self, info):
        """Resolver for getting number of conda3 packages in the labbook"""
        if self._package_manager_counts is None:
            return info.context.labbook_loader.load(f"{get_logged_in_username()}&{self.owner}&{self.name}").then(
                lambda labbook: self._get_all_package_manager_counts(labbook)['conda3'])

        return self._package_manager_counts['conda3']

    def resolve_num_pip_packages(self, info):
        """Resolver for getting number of pip packages in the labbook"""
        if self._package_manager_counts is None:
            return info.context.labbook_loader.load(f"{get_logged_in_username()}&{self.owner}&{self.name}").then(
                lambda labbook: self._get_all_package_manager_counts(labbook)['pip'])

        return self._package_manager_counts['pip']

    @staticmethod
    def helper_resolve_num_custom_dependencies(labbook):
        """Helper to count the number of custom deps"""
        custom_dir = os.path.join(labbook.root_dir, ".gigantum", "env", "custom")
        count = len([x for x in glob.glob(os.path.join(custom_dir, "*.yaml"))])
        return count

    def resolve_num_custom_dependencies(self, info):
        """Resolver for getting number of custom dependencies in the labbook"""
        return info.context.labbook_loader.load(f"{get_logged_in_username()}&{self.owner}&{self.name}").then(
            lambda labbook: self.helper_resolve_num_custom_dependencies(labbook))

    def help_resolve_recent_activity(self, labbook):
        """Method to create 1 activity records with show=True"""
        # Create instance of ActivityStore for this LabBook
        store = ActivityStore(labbook)

        record = None
        after = None
        while not record:
            items = store.get_activity_records(first=5, after=after)

            if not items:
                # if no more items, continue
                break

            for item in items:
                if item.show is True and item.num_detail_objects > 0:
                    record = ActivityRecordObject(id=f"labbook&{self.owner}&{self.name}&{item.commit}",
                                                  owner=self.owner,
                                                  name=self.name,
                                                  _repository_type='labbook',
                                                  commit=item.commit,
                                                  _activity_record=item)

                    break

                # Set after cursor to last commit
                after = item.commit

        return record

    def resolve_recent_activity(self, info):
        """Resolver for getting recent important activity"""
        return info.context.labbook_loader.load(f"{get_logged_in_username()}&{self.owner}&{self.name}").then(
            lambda labbook: self.help_resolve_recent_activity(labbook))

    def resolve_readme(self, info):
        """Resolve the readme document inside the labbook"""
        return info.context.labbook_loader.load(f"{get_logged_in_username()}&{self.owner}&{self.name}").then(
            lambda labbook: labbook.get_readme())


class DatasetOverview(graphene.ObjectType, interfaces=(graphene.relay.Node, GitRepository)):
    """A type representing the overview of a Dataset
    """
    _dataset_file_info = None

    # Dataset size information
    num_files = graphene.Int()
    total_bytes = graphene.String()
    local_bytes = graphene.String()

    # File type distribution in the format `.XX,.json`
    file_type_distribution = graphene.List(graphene.String)

    # Readme document for the Dataset
    readme = graphene.String()

    def _get_dataset_file_info(self, dataset) -> dict:
        """helper method to iterate over the manifest and get file info for the overview page

        Returns:
            None
        """
        m = Manifest(dataset, get_logged_in_username())

        count = 0
        total_bytes = 0
        file_type_distribution: OrderedDict = OrderedDict()
        for key in m.manifest:
            item = m.manifest[key]
            if key[-1] == '/':
                # Skip directories
                continue

            filename = os.path.basename(key)
            if filename[0] == '.':
                # Skip hidden files
                continue

            if '.' not in filename:
                # Skip files without an extension
                continue

            # Count file type distribution
            _, ext = os.path.splitext(filename)
            if ext:
                file_type = ext
                if file_type in file_type_distribution:
                    file_type_distribution[file_type] += 1
                else:
                    file_type_distribution[file_type] = 1

            # Count total file size
            total_bytes += int(item['b'])

            # Count files
            count += 1

        # Format the output for file type distribution
        formatted_file_type_info: List[str] = list()
        file_type_distribution = OrderedDict(sorted(file_type_distribution.items(),
                                                    key=itemgetter(1),
                                                    reverse=True))
        for file_type in file_type_distribution:
            percentage = float(file_type_distribution[file_type]) / float(count)
            formatted_file_type_info.append(f"{percentage:.2f}|{file_type}")

        self._dataset_file_info = {'num_files': count,
                                   'total_bytes': total_bytes,
                                   'local_bytes': count,
                                   'file_type_distribution': formatted_file_type_info
                                   }

        return self._dataset_file_info

    @classmethod
    def get_node(cls, info, id):
        """Method to resolve the object based on it's Node ID"""
        # Parse the key
        owner, name = id.split("&")

        return LabbookOverview(owner=owner, name=name)

    def resolve_id(self, info):
        """Resolve the unique Node id for this object"""
        if not self.id:
            if not self.owner or not self.name:
                raise ValueError("Resolving a LabbookOverview Node ID requires owner and name to be set")

            self.id = f"{self.owner}&{self.name}"

        return self.id

    def resolve_num_files(self, info):
        """Resolver for getting number of files in the dataset"""
        if self._dataset_file_info is None:
            return info.context.dataset_loader.load(f"{get_logged_in_username()}&{self.owner}&{self.name}").then(
                lambda dataset: self._get_dataset_file_info(dataset)['num_files'])

        return self._dataset_file_info['num_files']

    def resolve_total_bytes(self, info):
        """Resolver for getting total bytes of files in the dataset"""
        if self._dataset_file_info is None:
            return info.context.dataset_loader.load(f"{get_logged_in_username()}&{self.owner}&{self.name}").then(
                lambda dataset: self._get_dataset_file_info(dataset)['total_bytes'])

        return self._dataset_file_info['total_bytes']

    def resolve_file_type_distribution(self, info):
        """Resolver for getting the distribution of file types in the dataset"""
        if self._dataset_file_info is None:
            return info.context.dataset_loader.load(f"{get_logged_in_username()}&{self.owner}&{self.name}").then(
                lambda dataset: self._get_dataset_file_info(dataset)['file_type_distribution'])

        return self._dataset_file_info['file_type_distribution']

    @staticmethod
    def _helper_local_bytes(dataset):
        """Helper to compute total size of a dataset on disk"""
        m = Manifest(dataset, get_logged_in_username())
        total_size = 0

        for dirpath, dirnames, filenames in os.walk(m.current_revision_dir):
            for f in filenames:
                if f == '.smarthash':
                    continue
                fp = os.path.join(dirpath, f)
                total_size += os.path.getsize(fp)

        return total_size

    def resolve_local_bytes(self, info):
        """Resolver for getting total bytes of files in the dataset"""
        return info.context.dataset_loader.load(f"{get_logged_in_username()}&{self.owner}&{self.name}").then(
            lambda dataset: self._helper_local_bytes(dataset))

    def resolve_readme(self, info):
        """Resolve the readme document inside the dataset"""
        return info.context.dataset_loader.load(f"{get_logged_in_username()}&{self.owner}&{self.name}").then(
            lambda dataset: dataset.get_readme())
