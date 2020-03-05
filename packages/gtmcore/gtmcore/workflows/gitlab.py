import requests
import subprocess
import pexpect
import re
import os
from enum import Enum
from typing import List, Optional, Tuple, Dict, Any
from urllib.parse import quote_plus

from gtmcore.logging import LMLogger

logger = LMLogger.get_logger()
REQUEST_TIMEOUT = 30


def check_and_add_user(hub_api: str, access_token: str, id_token: str) -> None:
    """Method to check if a user exists in GitLab and if not, create it

    Args:
        hub_api(str): URL of the Gigantum Hub API
        access_token(str): The logged in user's access token
        id_token(str): The logged in user's id token

    Returns:
        None
    """
    # Use the "synchronizeUserAccount" mutation to ensure the user exists in the associated git backend
    query = """mutation {
                  synchronizeUserAccount(input: { clientMutationId: "1" }) {
                    gitUserId
                  }
                }"""

    response = requests.post(hub_api,
                             json={"query": query},
                             headers={'Authorization': f"Bearer {access_token}", 'Identity': id_token})

    if response.status_code != 200:
        logger.error(f"Failed to synchronize user account with git backend. Status Code: {response.status_code}")
        logger.error(response.json())
        raise GitLabException("Failed to synchronize user account with git backend")

    result = response.json()
    if "errors" in result:
        logger.error(f"Failed to synchronize user account with git backend. Status Code: {response.status_code}")
        logger.error(response.json())
        raise GitLabException(f"Failed to synchronize user account with git backend: {result.get('errors')}")


class GitLabException(Exception):
    pass


class StaleCredentialsException(GitLabException):
    pass


class Visibility(Enum):
    """ Represents access to remote GitLab project"""
    # Available only to owner and collaborators
    PRIVATE = "private"

    # Available to anyone via link (even non-users)
    PUBLIC = "public"

    # Available to any user registered in GitLab
    INTERNAL = "internal"


class ProjectPermissions(Enum):
    """ Represents a GitLab role -- taken from:
    https://docs.gitlab.com/ee/api/members.html"""

    # Represents a Gitlab "Reporter"
    READ_ONLY = 20

    # Represents a "Developer" (Basic read/write)
    READ_WRITE = 30

    # Represents a "Maintainer" (Essentially owner)
    OWNER = 40


class GitLabManager(object):
    """Class to manage administrative operations to a remote GitLab server"""
    def __init__(self, remote_host: str, hub_api: str, access_token: Optional[str], id_token: Optional[str]) -> None:
        """

        Args:
            remote_host: the domain of the remote git host
            hub_api: the url to the hub API
            access_token(str): The logged in user's access token
            id_token(str): The logged in user's id token
        """
        # GitLab Server URL
        self.remote_host = remote_host
        # Hub API URL
        self.hub_api = hub_api

        # Current user's bearer token
        self.access_token = access_token
        self.id_token = id_token

        # Current user's GitLab impersonation token
        self._gitlab_token: Optional[str] = None

    @staticmethod
    def get_repository_id(namespace: str, repository_name: str) -> str:
        """Method to transform a namespace and labbook name to a project ID

        Args:
            namespace(str): Namespace in gitlab, currently the "owner"
            repository_name(str): Repository name (i.e. project name in gitlab)

        Returns:
            str
        """
        return quote_plus(f"{namespace}/{repository_name}")

    def _hub_api_headers(self) -> Dict[str, str]:
        """Method to get the authorization and id headers for calling the hub api

        Returns:
            dict
        """
        if self.access_token is not None and self.id_token is not None:
            return {"Authorization": f"Bearer {self.access_token}",
                    "Identity": self.id_token}
        else:
            return dict()

    def _gitlab_api_headers(self) -> Dict:
        """Method to get the authorization and id headers for calling the gitlab api

        Returns:
            dict
        """
        if self.access_token is not None and self.id_token is not None:
            return {"PRIVATE-TOKEN": self._repo_token()}
        else:
            return dict()

    def _repo_token(self) -> Optional[str]:
        """Method to get the user's API token from the hub API"""
        if self.access_token is not None and self.id_token is not None:
            if self._gitlab_token is None:
                # Get the token
                query = """{
                              additionalCredentials {
                                gitServiceToken
                              }  
                            }"""

                response = requests.post(self.hub_api,
                                         json={"query": query},
                                         headers=self._hub_api_headers())

                if response.status_code != 200:
                    logger.error(f"Failed to get user access key from server. Status Code: {response.status_code}")
                    logger.error(response.json())
                    raise GitLabException("Failed to get user access key from server")

                result = response.json()
                if "errors" in result:
                    logger.error(f"Failed to get user access key from server. Status Code: {response.status_code}")
                    logger.error(response.json())
                    raise GitLabException(f"Failed to get user git token: {result.get('errors')}")

                self._gitlab_token = result['data']['additionalCredentials']['gitServiceToken']

            return self._gitlab_token
        else:
            # If access and ID token aren't set, don't try to get a gitlab tokens
            return None

    def _get_user_id_from_username(self, username: str) -> int:
        """Method to get a user's id in GitLab based on their username

        Args:
            username(str):

        Returns:
            int
        """
        # Call API to get ID of the user
        response = requests.get(f"https://{self.remote_host}/api/v4/users?username={username}",
                                headers=self._gitlab_api_headers(),
                                timeout=REQUEST_TIMEOUT)
        if response.status_code != 200:
            logger.error(f"Failed to query for user ID from username. Status Code: {response.status_code}")
            logger.error(response.json())
            raise ValueError("Failed to query for user ID from username.")

        user_id = None
        for user in response.json():
            if user['username'] == username:
                user_id = user['id']
                break

        if user_id is None:
            raise ValueError(f"User ID not found when querying by username: {username}")

        return user_id

    def repository_exists(self, namespace: str, repository_name: str) -> bool:
        """Method to check if the remote repository already exists

        Args:
            namespace(str): Namespace in gitlab, currently the "owner"
            repository_name(str): Repository name (i.e. project name in gitlab)

        Returns:
            bool
        """
        # Call API to check for project
        repo_id = self.get_repository_id(namespace, repository_name)
        response = requests.get(f"https://{self.remote_host}/api/v4/projects/{repo_id}",
                                headers=self._gitlab_api_headers(),
                                timeout=REQUEST_TIMEOUT)

        if response.status_code == 200:
            return True
        elif response.status_code == 404:
            return False
        else:
            msg = f"Failed to check if {namespace}/{repository_name} exists. Status Code: {response.status_code}"
            logger.error(msg)
            logger.error(response.json())
            raise ValueError(msg)

    def set_visibility(self, namespace: str, repository_name: str, visibility: str) -> None:
        """ Change public/private visibility for a given project

        Args:
            namespace: Owner or organization
            repository_name: Name of repository
            visibility: One of "public" or "private"

        Returns:
            None (Exception on failure)

        """
        repo_id = self.get_repository_id(namespace, repository_name)
        update_data = {'visibility': visibility}
        response = requests.put(f"https://{self.remote_host}/api/v4/projects/{repo_id}",
                                data=update_data, headers=self._gitlab_api_headers(),
                                timeout=REQUEST_TIMEOUT)
        if response.status_code != 200:
            msg = f"Could not set visibility for remote repository {namespace}/{repository_name} " \
                  f"to {visibility}: Status code {response.status_code}"
            raise ValueError(msg)

        details = self.repo_details(namespace, repository_name)
        if details.get('visibility') != visibility:
            raise ValueError(f"Visibility could not be set for {namespace}/{repository_name} to {visibility}")

    def repo_details(self, namespace: str, repository_name: str) -> Dict[str, Any]:
        """ Get all properties of a given Gitlab Repository, see API documentation
            at https://docs.gitlab.com/ee/api/projects.html#get-single-project.

            Args:
                namespace: Owner or organization
                repository_name: Name of repository

            Returns:
                Dict of repository properties, for keys see above link.
            """
        repo_id = self.get_repository_id(namespace, repository_name)
        response = requests.get(f"https://{self.remote_host}/api/v4/projects/{repo_id}",
                                headers=self._gitlab_api_headers(),
                                timeout=REQUEST_TIMEOUT)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            raise GitLabException(f"Remote GitLab repo {namespace}/{repository_name} not found")
        else:
            msg = f"Failed to check if {namespace}/{repository_name} exists. Status Code: {response.status_code}"
            logger.error(msg)
            logger.error(response.json())
            raise GitLabException(msg)

    def create_labbook(self, namespace: str, labbook_name: str, visibility: str) -> None:
        """Method to create the remote repository

        Args:
            namespace(str): Namespace in gitlab, currently the "owner"
            labbook_name(str): LabBook name (i.e. project name in gitlab)
            visibility(str): public, private (default), or internal.

        Returns:

        """
        if self.repository_exists(namespace, labbook_name):
            raise ValueError("Cannot create remote repository that already exists")

        # Raises ValueError if given visibility is not valid
        Visibility(visibility)

        data = {"name": labbook_name,
                "issues_enabled": False,
                "jobs_enabled": False,
                "wiki_enabled": False,
                "snippets_enabled": False,
                "shared_runners_enabled": False,
                # See: https://docs.gitlab.com/ee/api/projects.html#project-merge-method
                # We want all deconfliction done on client-side.
                "merge_method": "ff",
                "visibility": visibility,
                "public_builds": False,
                "request_access_enabled": False
                }

        # Call API to create project
        response = requests.post(f"https://{self.remote_host}/api/v4/projects",
                                 headers=self._gitlab_api_headers(),
                                 json=data, timeout=REQUEST_TIMEOUT)

        if response.status_code != 201:
            logger.error("Failed to create remote repository")
            logger.error(response.json())
            raise ValueError("Failed to create remote repository")
        else:
            logger.info(f"Created remote repository {namespace}/{labbook_name}")

    def remove_repository(self, namespace: str, repository_name: str) -> None:
        """Method to remove the remote repository

        Args:
            namespace(str): Namespace in gitlab, currently the "owner"
            repository_name(str): LabBook name (i.e. project name in gitlab)

        Returns:
            None
        """
        if not self.repository_exists(namespace, repository_name):
            raise ValueError("Cannot remove remote repository that does not exist")

        # Call API to remove project
        repo_id = self.get_repository_id(namespace, repository_name)
        response = requests.delete(f"https://{self.remote_host}/api/v4/projects/{repo_id}",
                                   headers=self._gitlab_api_headers(),
                                   timeout=REQUEST_TIMEOUT)

        if response.status_code != 202:
            logger.error(f"Failed to remove remote repository. Status Code: {response.status_code}")
            logger.error(response.json())
            raise ValueError("Failed to remove remote repository")
        else:
            logger.info(f"Deleted remote repository {namespace}/{repository_name}")

    def get_collaborators(self, namespace: str,
                          repository_name: str) -> List[Tuple[int, str, ProjectPermissions]]:
        """Method to get usernames and IDs of collaborators that have access to the repo

        Args:
            namespace(str): Namespace in gitlab, currently the "owner"
            repository_name(str): LabBook name (i.e. project name in gitlab)

        Returns:
            list of tuples (user-id, username, permission-type)
        """
        if not self.repository_exists(namespace, repository_name):
            raise ValueError("Cannot get collaborators of a repository that does not exist")

        # Call API to get all collaborators
        collaborators = list()
        page = 1
        per_page = 20
        repo_id = self.get_repository_id(namespace, repository_name)
        while True:
            response = requests.get(f"https://{self.remote_host}/api/v4/projects/{repo_id}/"
                                    f"members?page={page}&per_page={per_page}",
                                    headers=self._gitlab_api_headers(),
                                    timeout=REQUEST_TIMEOUT)

            if response.status_code != 200:
                logger.error(f"Failed to get remote repository collaborators for {repo_id}, page {page}")
                logger.error(response.json())
                raise ValueError("Failed to get remote repository collaborators")
            else:
                # Will load one of ProjectPermissions enum fields, else throwing value err
                c = [(x['id'], x['username'], ProjectPermissions(x['access_level'])) for x in response.json()]
                collaborators.extend(c)
                page += 1

                if len(c) < per_page:
                    break

        return collaborators

    def add_collaborator(self, namespace: str, labbook_name: str, username: str, role: ProjectPermissions) -> None:
        """Method to add a collaborator to a remote repository by username

        Args:
            namespace: Namespace in gitlab, currently the "owner"
            labbook_name: LabBook name (i.e. project name in gitlab)
            username: username to add
            role: One of ProjectPermissions values - ruleset for new collaborator

        Returns:
            list of all collaborators
        """
        if not self.repository_exists(namespace, labbook_name):
            raise ValueError("Cannot add a collaborator to a repository that does not exist")

        # Call API to get ID of the user
        user_id = self._get_user_id_from_username(username)

        # Call API to add a collaborator
        data = {"user_id": user_id,
                "access_level": role.value}
        repo_id = self.get_repository_id(namespace, labbook_name)
        response = requests.post(f"https://{self.remote_host}/api/v4/projects/{repo_id}/members",
                                 headers=self._gitlab_api_headers(),
                                 json=data,
                                 timeout=REQUEST_TIMEOUT)

        if response.status_code != 201:
            logger.error("Failed to add collaborator")
            logger.error(response.json())
            raise GitLabException("Failed to add collaborator")
        else:
            # Re-query for collaborators and return
            logger.info(f"Added {username} as a {role} to {labbook_name}")

    def delete_collaborator(self, namespace: str, labbook_name: str, username: str) -> None:
        """Method to remove a collaborator from a remote repository by user_id

        user id is used because it is assumed you've already listed the current collaborators

        Args:
            namespace(str): Namespace in gitlab, currently the "owner"
            labbook_name(str): LabBook name (i.e. project name in gitlab)
            username(str): username to remove

        Returns:
            None
        """
        if not self.repository_exists(namespace, labbook_name):
            raise ValueError("Cannot remove a collaborator to a repository that does not exist")

        # Lookup username
        user_id = self._get_user_id_from_username(username)

        # Call API to remove a collaborator
        repo_id = self.get_repository_id(namespace, labbook_name)
        response = requests.delete(f"https://{self.remote_host}/api/v4/projects/{repo_id}/members/{user_id}",
                                   headers=self._gitlab_api_headers(),
                                   timeout=REQUEST_TIMEOUT)

        if response.status_code != 204:
            logger.error("Failed to remove collaborator")
            logger.error(response.json())
            raise ValueError("Failed to remove collaborator")
        else:
            logger.info(f"Removed user id `{user_id}` as a collaborator to {labbook_name}")

    @staticmethod
    def _call_shell(command: str, input_list: Optional[List[str]] = None) -> Tuple[Optional[bytes], Optional[bytes]]:
        """Method to call shell commands, used to configure git client

        Args:
            command(str): command to send
            input_list(list): List of additional strings to send to the process

        Returns:
            tuple
        """
        # Start process
        p = subprocess.Popen(command, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)

        # If additional commands provided, send to stdin
        if input_list:
            for i in input_list:
                p.stdin.write(i.encode('utf-8'))
                p.stdin.flush()

        # Get output
        try:
            out, err = p.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            logger.warning(f"Subprocess timed-out while calling shell for git configuration")
            p.kill()
            out, err = p.communicate(timeout=5)

        return out, err

    # TODO #1214: This can be cleanly replaced with the stdin approach to working with `git credential`
    def _check_if_git_credentials_configured(self, host: str, username: str) -> Optional[str]:
        """

        Args:
            host:
            username:

        Returns:

        """
        # Get the current working dir
        cwd = os.getcwd()
        try:
            # Switch to the user's home dir (needed to make git config and credential saving work)
            os.chdir(os.path.expanduser("~"))
            child = pexpect.spawn("git credential fill")
            child.expect("")
            child.sendline("protocol=https")
            child.expect("")
            child.sendline(f"host={host}")
            child.expect("")
            child.sendline(f"username={username}")
            child.expect("")
            child.sendline("")
            i = child.expect(["Password for 'https://", r"password=[\w\-\._]+", pexpect.EOF])
        finally:
            # Switch back to where you were
            os.chdir(os.path.expanduser(cwd))
        if i == 0:
            # Not configured
            child.sendline("")
            return None
        elif i == 1:
            # Possibly configured, verify a valid string
            matches = re.finditer(r"password=[a-zA-Z0-9\-_!@#$%^&*]+", child.after.decode("utf-8"))

            token = None
            try:
                for match in matches:
                    _, token = match.group().split("=")
                    break
            except ValueError:
                # if string is malformed it won't split properly and you don't have a token
                pass

            if not token:
                child.sendline("")
            child.close()
            return token
        elif i == 2:
            # Possibly configured, verify a valid string
            matches = re.finditer(r"password=[a-zA-Z0-9\-_!@#$%^&*]+", child.before.decode("utf-8"))

            token = None
            try:
                for match in matches:
                    _, token = match.group().split("=")
                    break
            except ValueError:
                # if string is malformed it won't split properly and you don't have a token
                pass

            if not token:
                child.sendline("")
            child.close()
            return token

        else:
            return None

    # TODO #1214: This can be cleanly replaced with the stdin approach to working with `git credential`
    def configure_git_credentials(self, host: str, username: str) -> None:
        """Method to configure the local git client's credentials

        Args:
            host(str): GitLab hostname
            username(str): Username to authenticate

        Returns:
            None
        """
        # Check if already configured
        token = self._check_if_git_credentials_configured(host, username)

        if token is None:
            cwd = os.getcwd()
            try:
                os.chdir(os.path.expanduser("~"))
                child = pexpect.spawn("git credential approve")
                child.expect("")
                child.sendline("protocol=https")
                child.expect("")
                child.sendline(f"host={host}")
                child.expect("")
                child.sendline(f"username={username}")
                child.expect("")
                child.sendline(f"password={self._repo_token()}")
                child.expect("")
                child.sendline("")
                child.expect(["", pexpect.EOF])
                child.sendline("")
                child.expect(["", pexpect.EOF])
                child.close()
            finally:
                os.chdir(os.path.expanduser(cwd))

            logger.info(f"Configured local git credentials for {host}")

    # TODO #1214: This can be cleanly replaced with the stdin approach to working with `git credential`
    def clear_git_credentials(self, host: str) -> None:
        """Method to clear the local git client's credentials

        Args:
            host(str): GitLab hostname

        Returns:
            None
        """
        cwd = os.getcwd()
        try:
            child = pexpect.spawn("git credential reject")
            child.expect("")
            child.sendline("protocol=https")
            child.expect("")
            child.sendline(f"host={host}")
            child.expect("")
            child.sendline("")
            child.expect("")
            child.sendline("")
            child.expect("")
            child.sendline("")
            child.close()
        finally:
            os.chdir(os.path.expanduser(cwd))

        logger.info(f"Removed local git credentials for {host}")
