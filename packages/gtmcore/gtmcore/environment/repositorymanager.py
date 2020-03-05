import os
import yaml
import glob
import pickle
import operator
import requests
import shutil
from collections import OrderedDict
from typing import (Any, List, Optional)

from gtmcore.gitlib import get_git_interface
from gtmcore.logging import LMLogger
from gtmcore.configuration import Configuration

logger = LMLogger.get_logger()


def repo_url_to_name(url: str) -> str:
    """Method to generate a directory name from the repo URL for local storage

    Assumes URL of the form whatever/namespace/repo(.git)(@branch). SSH URLs will not work.

    Args:
        url(str): repository URL

    Returns:
        str
    """
    if "@" in url:
        url, branch = url.split("@")
    if url.endswith('.git'):
        url = url[:-4]
    _, namespace, repo = url.rsplit("/", 2)
    return "{}_{}".format(namespace, repo)


class RepositoryManager(object):
    """Class to manage local copies of Base Repositories
    """

    def __init__(self, config_file: str=None) -> None:
        """Constructor

        Args:
            config_file(str): Optional config file location if don't want to load from default location
        """
        self.config = Configuration(config_file=config_file)
        self.local_repo_directory = os.path.expanduser(os.path.join(self.config.config["git"]['working_directory'],
                                                       ".labmanager", "environment_repositories"))
        self.git = get_git_interface(self.config.config['git'])

    @staticmethod
    def _internet_is_available() -> bool:
        """Private method to check if the user can get to GitHub, since that is where the component repos are

        Returns:
            None
        """
        # Create the directory to clone into
        try:
            requests.head('https://github.com', timeout=15)
        except requests.exceptions.ConnectionError:
            return False

        return True

    def _update_repo(self, location: str, branch: Optional[str] = None) -> None:
        """Private method to update a repository

        Args:
            location: the directory containing the repository
            branch: any refspec acceptable to git (default is all configured remote branches, which defaults to all
              branches with a regular clone, or just the initial branch with a single-branch clone)

        Returns:
            None
        """
        # Set the gitlib to point to that directory
        self.git.set_working_directory(location)

        # Fetch the requested branch
        self.git.fetch(refspec=branch)
        # Using FETCH_HEAD is robust / easy when you aren't tracking all remote branches, but still might switch branches
        self.git.checkout('FETCH_HEAD')

    def update_repositories(self) -> bool:
        """Method to update all repositories in the LabManager configuration file

        If the repositories do not exist, they are cloned

        Returns:
            bool: flag indicting if repos updated successfully
        """
        if self._internet_is_available():
            # Get repo Urls
            repo_urls = self.config.config["environment"]["repo_url"]

            for repo_url in repo_urls:
                repo_dir_name = repo_url_to_name(repo_url)
                full_repo_dir = os.path.join(self.local_repo_directory, repo_dir_name)

                # Get branch if encoded in URL
                branch = None
                if "@" in repo_url:
                    repo_url, branch = repo_url.split("@")

                # Check if repo exists locally
                if not os.path.exists(full_repo_dir):
                    # Create the directory to clone into
                    os.makedirs(full_repo_dir)

                    # Clone the repo
                    self.git.clone(repo_url, full_repo_dir, branch, single_branch=True)
                else:
                    # Need to update
                    self._update_repo(full_repo_dir, branch)

            for existing_dir in [n for n in os.listdir(self.local_repo_directory)
                                 if os.path.isdir(os.path.join(self.local_repo_directory, n))]:
                if existing_dir not in [repo_url_to_name(r) for r in repo_urls]:
                    # We need to remove old component repos because they may be out of date
                    # and crash any further processing.
                    logger.warning(f"Removing old LabManager index repository {existing_dir}")
                    shutil.rmtree(os.path.join(self.local_repo_directory, existing_dir))
            return True
        else:
            return False

    def index_repository(self, repo_name: str) -> OrderedDict:
        """Method to 'index' a base image directory in a single environment component repository

        Currently, the `index` is simply an ordered dictionary of all of the base image components in the repo
        The dictionary contains the contents of the YAML files for every version of the component and is structured:

            {
                "<repo_name>": {
                    "info": { repo info stored in repo config.yaml }
                    "<base_image_name>": {
                        "<Major.Minor>": { YAML contents }, ...
                    }, ...
                }
            }

        Args:
            repo_name: The name of the repo cloned locally
            component: One of 'base' or 'custom'
        Returns:
            OrderedDict
        """
        # Get full path to repo
        repo_dir = os.path.join(self.local_repo_directory, repo_name)

        # Get all base image YAML files
        # E.g., repo/*/*.yaml
        yaml_files = glob.glob(os.path.join(repo_dir, "*", "*.yaml"))

        data: OrderedDict[str, Any] = OrderedDict()
        data[repo_name] = OrderedDict()

        # Read YAML files and write data to dictionary
        for yf in yaml_files:
            with open(yf, 'rt', encoding='utf8') as yf_file:
                yaml_data = yaml.safe_load(yf_file)
                _, component_name, _ = yf.rsplit(os.path.sep, 2)

                # Save the COMPONENT repository to aid in accessing components via API
                # Will pack this info into the `component` field for use in mutations to access the component
                yaml_data["repository"] = repo_name

                if component_name not in data[repo_name]:
                    data[repo_name][component_name] = OrderedDict()

                revision = yaml_data['revision']
                data[repo_name][component_name][revision] = yaml_data

        return data

    @staticmethod
    def build_base_list_index(index_data: OrderedDict) -> List:
        """Method to convert the structured index of all versions into a flat list with only the latest version

        Returns:
            list
        """
        base_list = []
        repos = list(index_data.keys())
        for repo in repos:
            if repo == 'info':
                # ignore the repository info section
                continue

            bases = list(index_data[repo].keys())

            for base in bases:
                # Sort based on the revision
                revs = list(index_data[repo][base].items())
                revs = sorted(revs, reverse=True, key=operator.itemgetter(0))
                base_list.append(revs[0][1])

        return sorted(base_list, key=lambda n: n['id'])

    def index_repositories(self) -> None:
        """Method to index repos using a naive approach

        Stores index data in a pickled dictionaries in <working_directory>/.labmanager/environment_repositories/.index/

        Returns:
            None
        """
        # Get all local repos
        repo_urls = self.config.config["environment"]["repo_url"]
        repo_names = [repo_url_to_name(x) for x in repo_urls]

        base_image_all_repo_data: OrderedDict = OrderedDict()
        for repo_name in repo_names:
            # Index Base Images
            base_image_all_repo_data.update(self.index_repository(repo_name))

        # Generate list index
        base_image_list_repo_data = self.build_base_list_index(base_image_all_repo_data)

        # Write files
        with open(os.path.join(self.local_repo_directory, "base_index.pickle"), 'wb') as fh:
            pickle.dump(base_image_all_repo_data, fh)
        with open(os.path.join(self.local_repo_directory, "base_list_index.pickle"), 'wb') as fh:
            pickle.dump(base_image_list_repo_data, fh)