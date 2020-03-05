import hashlib
import os
import time
from abc import ABC, abstractmethod
from typing import Optional, Callable, List, Dict, Any

from gtmcore.configuration import Configuration
from gtmcore.container.cuda import should_launch_with_cuda_support
from gtmcore.dataset.cache import get_cache_manager_class
from gtmcore.inventory.inventory import InventoryManager, InventoryException
from gtmcore.logging import LMLogger
from gtmcore.labbook import LabBook
from gtmcore.gitlib.git import GitAuthor

from gtmcore.container.exceptions import ContainerException

logger = LMLogger.get_logger()


class ContainerOperations(ABC):
    """Represents the interface to perform Docker-related operations for Gigantum projects.
    This includes, building, running, port-mapping, etc.
    """

    def __init__(self, username: str, labbook: Optional[LabBook] = None, path: Optional[str] = None,
                 override_image_name: Optional[str] = None):
        """Establish the core attributes we can expect in all subclasses

        Args:
            username: the logged-in Gigantum username (or a special-purpose username)
            labbook: if provided, it is assumed that labbook.name and labbook.owner are populated (including from a path)
            path: (ignored if labbook is not None) a path where we can load a LabBook from
            override_image_name: should be set programmatically if we can obtain labbok owner and name, and there's no
                "override" image "tag"
        """
        self.username = username

        if override_image_name:
            # If manually setting the image name, use it for the tag.
            self.image_tag = override_image_name

        if labbook:
            if path:
                logger.warning('path ignored when labbook is specified')
            self.labbook = labbook
        elif path:
            self.labbook = InventoryManager().load_labbook_from_directory(path)
        else:
            # We are running with a "bare" instance. Explicit container names will be necessary (where relevant)
            # Skipping the env_dir and image_tag logic below
            return

        self.env_dir = os.path.join(self.labbook.root_dir, '.gigantum', 'env')

        # Some important checks
        if not self.labbook.owner:
            raise ContainerException(f"{str(self.labbook)} has no owner")
        if not os.path.exists(self.env_dir):
            raise ValueError(f'Expected env directory `{self.env_dir}` does not exist.')

        if not override_image_name:
            # If you haven't manually set the image tag, load the default tag AFTER the labbook instance has been loaded
            self.image_tag = self.default_image_tag(self.labbook.owner, self.labbook.name)

    @abstractmethod
    def build_image(self, nocache: bool = False, feedback_callback: Optional[Callable] = None) -> None:
        """Build a new docker image from the Dockerfile in the labbook's `.gigantum/env` directory.

        This image should be named by the self.image_tag attribute.

        Also note - This will delete any existing (but out-of-date) image pertaining to the given labbook.
        Thus if this call fails, there will be no docker images pertaining to that labbook.

        Args:
            nocache: Don't user the Docker cache if True
            feedback_callback: a function taking a str as it's sole argument to report progress back to the caller

        Raises:
            ContainerBuildException if container build fails.
        """
        raise NotImplementedError()

    @abstractmethod
    def delete_image(self, override_image_name: Optional[str] = None) -> bool:
        """ Delete the Docker image for the given LabBook

        Args:
            override_image_name: Alternate Tag of docker image (optional)

        Returns:
            Did we succeed?
        """
        raise NotImplementedError()

    @abstractmethod
    def image_available(self) -> bool:
        """Do we currently see an up-to-date Docker image?

        Returns:
            True if we have an Image ID stored.
        """
        raise NotImplementedError()

    @abstractmethod
    def exec_command(self, command: str, container_name: Optional[str] = None, get_results=False, **kwargs) \
            -> Optional[str]:
        """Run a command inside a given container, defaulting to the Project container.

        Args:
            command: e.g., 'ls -la'. This will be tokenized
            container_name: ID string of container in which to run - currently not actually used!
            kwargs: see implementation for allowed keys, passed to `exec_run` in docker-py

        Returns:
            If detach is False (or unspecified), a str with output of the command.
            Otherwise, None.
        """
        raise NotImplementedError()

    def ps_search(self, ps_name: str, container_name: Optional[str] = None, reps: int = 10) -> List[str]:
        """Exec ps and grep in the container to check for a process

        ps_name should NOT include any extra quotes (it will be surrounded by single-quotes in the shell command)

        Args:
            ps_name: the string that we'll use to grep `ps` output
            container_name: any name that works for Docker
            reps: number of repetitions (currently 1 second per loop).
                 Note, an INFO log will be made if reps > 1 (the default)

        Returns:
            A list of matching processes
        """
        for timeout in range(reps):
            ps_output = self.exec_command(f"ps aux | grep '{ps_name}'", container_name=container_name, get_results=True)
            if ps_output:  # Needed for mypy given abstractmethod
                ps_list = [l for l in ps_output.split('\n') if l and 'grep' not in l]
                ps_list = [l for l in ps_list if 'init -- ' not in l]
                if ps_list:
                    if reps > 1:
                        # We assume we're searching for a process, so we log how long it took to come up
                        logger.info(f"{ps_name} found after {timeout} seconds")
                    return ps_list

            # Pause briefly to avoid race conditions
            time.sleep(1)

        # ps_list is also [], but this is more clear
        return []

    @abstractmethod
    def run_container(self, cmd: Optional[str] = None, image_name: Optional[str] = None, environment: List[str] = None,
                      volumes: Optional[Dict] = None, wait_for_output=False, container_name: Optional[str] = None,
                      **run_args) \
            -> Optional[str]:
        """ Start a Docker container, by default for the Project connected to this instance.

        The container should be reachable from the Client network.

        Args:
            cmd: override the default cmd for the image
            image_name: use a different image than the current build for this Project
            environment: modeled on the containers.run() API
            volumes: same
            wait_for_output: should the method collect and return stdout? If so, container is anonymous and will be deleted.
            container_name: by default, container_name will be the same as image_name. Override by passing this argument
            run_args: any other args are passed to containers.run()

        Returns:
            If wait_for_output is specified, the stdout of the cmd. Otherwise, or if stdout cannot be obtained, None.
        """
        raise NotImplementedError()

    def start_project_container(self, author: Optional[GitAuthor] = None) -> None:
        """Start the Docker container for the Project connected to this instance.

        This method sets the Client IP to the environment variable `GIGANTUM_CLIENT_IP`

        If author is provided, `GIGANTUM_EMAIL` and `GIGANTUM_USERNAME` env vars are set

        All relevant configuration for a fully functional Project is set up here, then passed off to
         self.run_container()
         
        Args:
             author: Optionally provide a GitAuthor instance to configure the save hook
         
        """
        if not self.labbook:
            raise ValueError('labbook must be specified for run_container')

        if not os.environ.get('HOST_WORK_DIR'):
            raise ValueError("Environment variable HOST_WORK_DIR must be set")

        mnt_point = self.labbook.root_dir.replace('/mnt/gigantum', os.environ['HOST_WORK_DIR'])
        volumes_dict = {
            mnt_point: {'bind': '/mnt/labbook', 'mode': 'cached'},
            'labmanager_share_vol': {'bind': '/mnt/share', 'mode': 'rw'}
        }

        # Set up additional bind mounts for datasets if needed.
        datasets = InventoryManager().get_linked_datasets(self.labbook)
        for ds in datasets:
            try:
                cm_class = get_cache_manager_class(ds.client_config)
                cm = cm_class(ds, self.username)
                ds_cache_dir = cm.current_revision_dir.replace('/mnt/gigantum', os.environ['HOST_WORK_DIR'])
                volumes_dict[ds_cache_dir] = {'bind': f'/mnt/labbook/input/{ds.name}', 'mode': 'ro'}
            except InventoryException:
                continue

        # If re-mapping permissions, be sure to configure the container
        if 'LOCAL_USER_ID' in os.environ:
            env_var = [f"LOCAL_USER_ID={os.environ['LOCAL_USER_ID']}"]
        else:
            env_var = ["WINDOWS_HOST=1"]

        # If an author is provided, configure env vars for the save hook
        if author:
            env_var.append(f'GIGANTUM_USERNAME={author.name}')
            env_var.append(f'GIGANTUM_EMAIL={author.email}')

        # Set the client IP in the project container
        try:
            gigantum_client_ip = self.get_gigantum_client_ip()
        except ContainerException as e:
            logger.warning(e)
            gigantum_client_ip = ""

        env_var.append(f"GIGANTUM_CLIENT_IP={gigantum_client_ip}")

        # Get resource limits
        resource_args = dict()
        memory_limit = self.labbook.client_config.config['container']['memory']
        cpu_limit = self.labbook.client_config.config['container']['cpu']
        gpu_shared_mem = self.labbook.client_config.config['container']['gpu_shared_mem']
        if memory_limit:
            # If memory_limit not None, pass to Docker to limit memory allocation to container
            resource_args["mem_limit"] = memory_limit
        if cpu_limit:
            # If cpu_limit not None, pass to Docker to limit CPU allocation to container
            # "nano_cpus" is an integer in factional parts of a CPU
            resource_args["nano_cpus"] = round(cpu_limit * 1e9)

        # run with nvidia-docker if we have GPU support on the Host compatible with the project
        should_run_nvidia, reason = should_launch_with_cuda_support(self.labbook.cuda_version)
        if should_run_nvidia:
            logger.info(f"Launching container with GPU support:{reason}")
            if gpu_shared_mem:
                resource_args["shm_size"] = gpu_shared_mem
                resource_args['runtime'] = 'nvidia'

        else:
            logger.info(f"Launching container without GPU support. {reason}")

        self.run_container(environment=env_var, volumes=volumes_dict, **resource_args)

    @abstractmethod
    def stop_container(self, container_name: Optional[str] = None) -> bool:
        """ Stop a container, defaults to the Project container.

        Returns:
            A boolean indicating whether the container was successfully stopped (False can simply imply no container
            was running).
        """
        raise NotImplementedError()

    @abstractmethod
    def query_container(self, container_name: Optional[str] = None) -> Optional[str]:
        """Query the given container and get its status. E.g., "running" or "stopped"

        Returns:
            String of container status - "stopped", "running", etc., or None if container can't be loaded
        """
        raise NotImplementedError()

    @abstractmethod
    def query_container_ip(self, container_name: Optional[str] = None) -> Optional[str]:
        """Query the given container's IP address. Defaults to the Project container for this instance.

        Args:
            container_name: alternative to the current project container. Use anything that works for containers.get()

        Returns:
            IP address as string, None if not available (e.g., container doesn't exist)
        """
        raise NotImplementedError()

    @abstractmethod
    def query_container_env(self, container_name: Optional[str] = None) -> List[str]:
        """Get the list of environment variables from the container

        Args:
            container_name: an optional container name (otherwise, will use self.image_tag)

        Returns:
            A list of strings like 'VAR=value'
        """
        raise NotImplementedError()

    @abstractmethod
    def copy_into_container(self, src_path: str, dst_dir: str):
        """Copy the given file in src_path into the project's container.

        Args:
            src_path: Source path ON THE HOST of the file - callers responsibility to sanitize
            dst_dir: Destination directory INSIDE THE CONTAINER.
        """
        raise NotImplementedError()

    # Utility methods - might use across contexts, but can also override.

    def default_image_tag(self, owner: str, labbook_name: str) -> str:
        """The way we name our image for a Project on a local Docker instance

        This is not quite a tag. It's passed in to the `tag()` function, but it's used for Image and Container names.

        Args:
            owner: of the project - maps to the second username in the local gigantum directory hierarchy
            labbook_name: maps to the directory name for the project in the local gigantum hierarchy

        Returns:
            Our default name for a given project, used for both Image and Container names.
        """
        return f"gmlb-{self.username}-{owner}-{labbook_name}"

    # TODO #1062 - this has nothing to do with (directly) managing comtainers except for a naming scheme. Can we move to
    #  ComponentManager or some more related location? Do AFTER the cloud API is implemented.
    @staticmethod
    def check_cached_hash(image_tag: str, env_dir: str, update_cache=True) -> str:
        """Determine if the environment changed since last we checked

        NOTE - only call with update_cache=True in the context when the API requests building a new image! I.e., likely
        only call from within .build_image(). Otherwise, the cached hash may be updated without updating the image
        itself.

        Args:
            image_tag: the "key" where we'll use to look up / store environment hashes
            env_dir: a directory where we can find a gigantum environment specification
            update_cache: Update the cache stored on the filesystem?

        Returns:
            'not cached', 'match', or 'changed'
        """
        cache_dir = '/mnt/gigantum/.labmanager/image-cache'
        if not os.path.exists(cache_dir):
            logger.info(f"Making environment cache at {cache_dir}")
            os.makedirs(cache_dir, exist_ok=True)
        env_cache_path = os.path.join(cache_dir, f"{image_tag}.cache")

        # Make a hash of the environment specification, by
        m = hashlib.sha256()
        for root, dirs, files in os.walk(env_dir):
            for f in [n for n in files if '.yaml' in n]:
                m.update(os.path.join(root, f).encode())
                m.update(open(os.path.join(root, f)).read().encode())
        env_cksum = m.hexdigest()
        old_env_cksum: Optional[str] = None
        if os.path.exists(env_cache_path):
            old_env_cksum = open(env_cache_path).read()
        else:
            with open(env_cache_path, 'w') as cfile:
                cfile.write(env_cksum)

        if not old_env_cksum:
            return 'not cached'
        elif env_cksum == old_env_cksum:
            return 'match'
        else:
            # Env checksum hash is outdated. Remove it.
            os.remove(env_cache_path)
            if update_cache:
                with open(env_cache_path, 'w') as cfile:
                    cfile.write(env_cksum)

            return 'changed'

    @abstractmethod
    def get_gigantum_client_ip(self) -> Optional[str]:
        """Method to get the monitored lab book container's IP address on the Docker bridge network

        Returns:
            str of IP address
        """
        raise NotImplementedError()

    @abstractmethod
    def open_ports(self, port_list: List[int]) -> None:
        """A method to dynamically open ports to a running container. Locally this isn't really needed, but in the hub
        it is required

        Args:
            port_list: list of ports to open

        Returns:
            None
        """
        raise NotImplementedError()

    @abstractmethod
    def configure_dev_tool(self, dev_tool: str) -> None:
        """A method to configure a dev tool if needed. This is to be inserted right before starting the tool process,
        so it lets you configure things after the giguser is created and everything is set up, but before the dev
        tool process starts. This method exists here, because projects running in different contexts (e.g. hub, local)
        may require different configuration.

        Args:
            dev_tool: dev tool to configure (i.e jupyterlab, notebook, rstudio)

        Returns:
            None
        """
        raise NotImplementedError()


class SidecarContainerOperations:
    """Keep track of containers related to a parent (for now, Project) container"""

    def __init__(self, primary_container: ContainerOperations, sidecar_name: str):
        """Set up names for things

        Args:
            primary_container: who are we a sidecar for?
            sidecar_name: a tag that helps us keep track of what this sidecar does (e.g., `mitmproxy`)
        """
        if not primary_container.image_tag:
            raise ValueError('primary_container needs a concrete image tag.')

        self.primary_container = primary_container
        self.sidecar_name = sidecar_name
        self.sidecar_container_name = '.'.join((sidecar_name, primary_container.image_tag))

    def run_container(self, image_name: str, volumes: Optional[Dict] = None, environment: Optional[List] = None,
                      cmd: Optional[str] = None):
        """Run the sidecar container

        Args:
            image_name: a valid docker image
            volumes: a dict that complies with the docker-py API for specifying volumes
            environment: a list of strings like "VAR=something"
            cmd: (discouraged - sidecars should be simple) override the default CMD

        Returns:
            The IP address of the new container as a string
        """
        self.primary_container.run_container(cmd=cmd, image_name=image_name, container_name=self.sidecar_container_name,
                                             volumes=volumes, environment=environment)

        return self.primary_container.query_container_ip(self.sidecar_container_name)

    def stop_container(self):
        return self.primary_container.stop_container(container_name=self.sidecar_container_name)

    def query_container(self):
        return self.primary_container.query_container(self.sidecar_container_name)

    def ps_search(self, ps_name, reps=10):
        return self.primary_container.ps_search(ps_name, self.sidecar_container_name, reps)

    def query_container_env(self) -> List[str]:
        return self.primary_container.query_container_env(self.sidecar_container_name)

    def query_container_ip(self) -> Optional[str]:
        return self.primary_container.query_container_ip(self.sidecar_container_name)


# We only want to hit the filesystem once to get this value (otherwise, we parse the config file for every container
# operation). This is used ONLY in container_for_context() below. Context-specific logic should otherwise be contained
# in the subclasses.
CONTEXT = Configuration().config['container']['context']


def container_for_context(username: str, labbook: Optional[LabBook] = None, path: Optional[str] = None,
                          override_image_name: Optional[str] = None) -> ContainerOperations:
    """Instantiate an instance that can build images and run containers via Docker.

    Context is obtained via the standard configuration file from build time + overrides in
    ~/gigantum/.labmanager/config.yaml

    The signature is isomorphic with the init for subclasses of ContainerOperations.

    Args:
        username (required): username logged into the client
        labbook: a LabBook object
        path: a directory where we can find a project - ignored when labbook is given
        override_image_name: optional name to use instead of our default for username+labbook, can often also be
            specified in individual methods

    Returns:
        A subclass of ContainerOperations depending on the value of context (looked up in the above global var)
    """
    if CONTEXT == 'local':
        # We do the import here to (1) avoid circular dependencies and (2) allow for any crazy run-time logic for
        # the cloud
        from gtmcore.container.local_container import LocalProjectContainer
        return LocalProjectContainer(username, labbook, path, override_image_name)
    elif CONTEXT == 'hub':
        from gtmcore.container.hub_container import HubProjectContainer
        return HubProjectContainer(username, labbook, path, override_image_name)
    else:
        raise NotImplementedError(f'"{CONTEXT}" support for ContainerOperations not yet supported')


def _check_allowed_args(provided_args: Dict[str, Any], allowed_args: set):
    """Check that provided_args contains only keys are are present in allowed_args

    Because of the deep usage of kwargs in docker-py, and the difficulty of finding default values, we can use this
    approach to control the surface of what we have to support across platforms in the method
    signature.
    """
    extra_args = set(provided_args.keys()) - allowed_args
    if extra_args:
        raise NotImplementedError(f'Unsupported arguments: {", ".join(extra_args)}')
