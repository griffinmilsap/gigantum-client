import json
import os
import socket
import tarfile
import tempfile
import time
from typing import Optional, Callable, List, Dict

import docker
import docker.errors
from docker import DockerClient, from_env
from docker.models.containers import Container

from gtmcore.container.container import ContainerOperations, _check_allowed_args, logger
from gtmcore.container.exceptions import ContainerBuildException, ContainerException

from gtmcore.labbook import LabBook


class LocalProjectContainer(ContainerOperations):
    """Implementation of ContainerOperations for a local context

    The assumption is that files local to the caller can be mounted to containers, and
    we are directly accessing the Docker Daemon
    """
    def __init__(self, username: str, labbook: Optional[LabBook] = None, path: Optional[str] = None,
                 override_image_name: Optional[str] = None):
        """Set up local Docker access and proceed to standard superclass init

        Args:
            username: the logged-in Gigantum username (or a special-purpose username)
            labbook: if provided, it is assumed that labbook.name and labbook.owner are populated (including from a path)
            path: (ignored if labbook is not None) a path where we can load a LabBook from
            override_image_name: should be set programmatically if we can obtain labbok owner and name, and there's no
                "override" image "tag"
        """
        self._client = get_docker_client()

        # We can populate _image_id with .build_image() or .image_available(),
        # the latter doesn't check the environment hash and is fast
        self._image_id: Optional[str] = None
        self._container: Optional[Container] = None

        ContainerOperations.__init__(self, username, labbook=labbook, path=path,
                                     override_image_name=override_image_name)

    # Manipulating images

    def build_image(self, nocache: bool = False, feedback_callback: Optional[Callable] = None) -> None:
        """"Build a new docker image from the Dockerfile in the labbook's `.gigantum/env` directory.

        This image will be named by the self.image_tag attribute.

        Also note - This will delete any existing (but out-of-date) image pertaining to the given labbook.
        Thus if this call fails, there will be no docker images pertaining to that labbook.

        Args:
            nocache: Don't user the Docker cache if True
            feedback_callback: a function taking a str as it's sole argument to report progress back to the caller

        Raises:
            ContainerBuildException if container build fails.
        """
        if not (self.image_tag and self.env_dir):
            raise ValueError("Cannot build an image without image_tag and env_dir")

        logger.info(f"Building docker image for {str(self.labbook or 'context without labbook')}, "
                    f"using name `{self.image_tag}`")

        if (not self._image_id) and \
                self.check_cached_hash(self.image_tag, self.env_dir) == 'match':
            try:
                self._image_id = self._client.images.get(name=self.image_tag).id
            except docker.errors.ImageNotFound:
                pass

        # Note: self._image_id is updated in the above conditional!
        if self._image_id:
            logger.info(f"Reusing Docker image for {str(self.labbook)}")
            if feedback_callback:
                feedback_callback(f"Reusing image {self._image_id}\n")
            return

        # We need to build the image
        try:
            # From: https://docker-py.readthedocs.io/en/stable/api.html#docker.api.build.BuildApiMixin.build
            # This builds the image and generates output status text.
            status_counter = 0
            for line in self._client.api.build(path=self.env_dir, tag=self.image_tag, pull=True, nocache=nocache,
                                               forcerm=True):
                ldict = json.loads(line)
                stream = (ldict.get("stream") or "")
                if feedback_callback:
                    feedback_callback(stream)

                # Unlike the stream above, which reports the results of running commands, status is more of an ongoing
                # report and will keep returning the same status over and over
                status = (ldict.get("status") or "")
                if feedback_callback and status:
                    if status.startswith('Digest:') or status.startswith('Status:'):
                        feedback_callback('\n' + status)
                    else:
                        # The details aren't that important. We just want to convey that something's happening
                        if status_counter == 0:
                            feedback_callback('. ')
                        status_counter = (status_counter + 1) % 5

                if 'successfully built' in stream.lower():
                    # When built, final line is in form of "Successfully built 02faas3"
                    # There is no other (simple) way to grab the image ID
                    _, self._image_id = stream.rsplit(maxsplit=1)

        except docker.errors.BuildError as e:
            self.delete_image()
            raise ContainerBuildException(e)

        if not self._image_id:
            # We could've gotten an empty string above
            self._image_id = None
            self.delete_image()
            if self.labbook:
                raise ContainerBuildException(f"Cannot determine docker image on LabBook from {self.labbook.root_dir}")
            else:
                raise ContainerBuildException(f"Cannot determine docker image, no LabBook specified")

    def delete_image(self, override_image_name: Optional[str] = None) -> bool:
        """ Delete the Docker image for the given LabBook

        Args:
            override_image_name: Alternate Tag of docker image (optional)

        Returns:
            Did we succeed? (includes image already non-existent)
        """
        if override_image_name:
            image_name = override_image_name
            image_msg = image_name
        elif self.image_tag:
            image_name = self.image_tag
            image_msg = str(self.labbook)
        else:
            raise ContainerException('No way to determine image name. Please provide override_image_name.')
        logger.info(f"Deleting docker image for {image_msg}")

        try:
            self._client.images.remove(image_name)
            logger.info(f"Deleted docker image for {image_msg}: {image_name}")
            if not override_image_name:
                self._image_id = None
        except docker.errors.ImageNotFound:
            logger.warning(f"Could not delete docker image for {image_msg}: {image_name} not found")
        except Exception as e:
            logger.error(f"Error deleting docker images for {image_msg}: {e}")
            return False

        return True

    def image_available(self) -> bool:
        """Do we currently see an up-to-date Docker image?

        Returns:
            True if we've gotten an Image ID stored.
        """
        if not self._image_id:
            try:
                self._image_id = self._client.images.get(name=self.image_tag).id
                return True
            except docker.errors.ImageNotFound:
                return False
        else:
            return True

    # Working with Containers

    def run_container(self, cmd: Optional[str] = None, image_name: Optional[str] = None, environment: List[str] = None,
                      volumes: Optional[Dict] = None, wait_for_output=False, container_name: Optional[str] = None,
                      **run_args) \
            -> Optional[str]:
        """ Start a Docker container, by default for the Project connected to this instance.

        The container should be reachable from the Client network.

        WARNING - wait_for_output by design may lead to an infinite loop. Be careful!

        Args:
            cmd: override the default cmd for the image
            image_name: use a different image than the current build for this Project
            environment: modeled on the containers.run() API
            volumes: same
            wait_for_output: should the method collect and return stdout?
            container_name: by default, container_name will be the same as image_name. Override by passing this argument
            run_args: any other args are passed to containers.run()

        Returns:
            If wait_for_output is specified, the stdout of the cmd. Otherwise, or if stdout cannot be obtained, None.
        """
        # We move a number of optional arguments into a **kwargs construct because
        #  no default value is specified in docker-py docs
        if volumes:
            run_args['volumes'] = volumes
        if environment:
            run_args['environment'] = environment
        if cmd:
            run_args['command'] = cmd

        image_name = image_name or self.image_tag
        if not image_name:
            raise ContainerException('No default image_name is available. Please specify at init or as a parameter.')

        if not wait_for_output:
            container_name = container_name or image_name
            # We use negative logic because this branch is much simpler
            container_object = self._client.containers.run(image_name, detach=True, init=True, name=container_name,
                                                           **run_args)
            if container_name == image_name:
                self._container = container_object
            return None
        else:
            t0 = time.time()
            result = self._client.containers.run(image_name, detach=False, init=True, remove=True, stderr=False,
                                                 **run_args)

            ts = time.time()
            if ts - t0 > 5.0:
                logger.warning(f'Command ({cmd or "default CMD"}) in {image_name} took {ts - t0:.2f} sec')

            return result.decode()

    def stop_container(self, container_name: Optional[str] = None) -> bool:
        """ Stop the given labbook.

        If there's an exception other than a NotFound, that exception is raised.

        Returns:
            A boolean indicating whether the container was successfully stopped (False implies no container
            was running).
        """
        if container_name:
            logger.info(f"Stopping {container_name}")
        elif self.labbook:
            logger.info(f"Stopping {str(self.labbook)} ({self.labbook.name})")
        else:
            raise ValueError(
                'Specify labbook, path, or override_image_name at init, or use explicit container_name arg')

        container = self._get_container(container_name)
        if container is None:
            return False

        container.stop(timeout=15)
        container.remove()

        if not container_name:
            self._container = None

        return True

    def query_container(self, container_name: Optional[str] = None) -> Optional[str]:
        """Query the Project container and get its status. E.g., "running" or "stopped"

        Also caches a Container instance in self._container.

        Returns:
            String of container status - "stopped", "running", etc., or None if container is NotFound
        """
        # This does a reload if we already have a container object
        container = self._get_container(container_name)

        if container:
            return container.status
        else:
            return None

    def exec_command(self, command: str, container_name: Optional[str] = None, get_results=False, **kwargs) \
            -> Optional[str]:
        """Run a command inside a given container, defaulting to the Project container.

        Args:
            command: e.g., 'ls -la'. This will be tokenized
            container_name: ID string of container in which to run
            get_results: Don't detach - instead wait for the command to finish and return the output as a str
            kwargs: see below for allowed keys, passed to `exec_run` in docker-py

        Returns:
            If get_results is True (or unspecified), a str with output of the command.
            Otherwise, None.
        """
        _check_allowed_args(kwargs, {'user', 'environment'})

        container = self._get_container(container_name)
        if container is None:
            return None

        detach = not get_results
        # We can't run `command` directly, even using `shlex.split` because we sometimes use multiple commands,
        # e.g., linked with `&&`
        exec_result = container.exec_run(f'sh -c "{command}"', detach=detach, **kwargs)

        if get_results:
            exit_code, output = exec_result
            return output.decode()
        else:
            return None

    def query_container_ip(self, container_name: Optional[str] = None) -> Optional[str]:
        """Query the given container's IP address. Defaults to the Project container for this instance.

        Args:
            container_name: alternative to the current project container. Use anything that works for containers.get()

        Returns:
            IP address as string, None if not available (e.g., container doesn't exist)
        """
        container = self._get_container(container_name)
        if container is None:
            return None

        # We hammer repeatedly for 5 seconds
        for _ in range(10):
            container.reload()
            container_ip = container.attrs['NetworkSettings']['Networks']['bridge']['IPAddress']
            if container_ip:
                # Not sure strip does anything, but calling code was doing it...
                return container_ip.strip()

            time.sleep(0.5)

        return None

    def query_container_env(self, container_name: Optional[str] = None) -> List[str]:
        """Get the list of environment variables from the container

        Args:
            container_name: an optional container name (otherwise, will use self.image_tag)

        Returns:
            A list of strings like 'VAR=value'
        """
        container = self._get_container(container_name)
        if container is None:
            return []

        return container.attrs['Config']['Env']

    def copy_into_container(self, src_path: str, dst_dir: str):
        """Copy the given file in src_path into the project's container.

        Args:
            src_path: Source path ON THE HOST of the file - callers responsibility to sanitize
            dst_dir: Destination directory INSIDE THE CONTAINER.
        """
        if not self.labbook:
            raise ContainerException('No LabBook provided at init')

        if not os.path.isfile(src_path):
            raise ContainerException(f"Source file {src_path} is not a file")

        self.exec_command(f"mkdir -p {dst_dir}", user='giguser')

        # Tar up the src file to copy into container
        tarred_secret_file = tempfile.NamedTemporaryFile()
        t = tarfile.open(mode='w', fileobj=tarred_secret_file)
        abs_path = os.path.abspath(src_path)
        t.add(abs_path, arcname=os.path.basename(src_path), recursive=True)
        t.close()
        tarred_secret_file.seek(0)

        try:
            logger.info(f"Copying file {src_path} into {dst_dir} in {str(self.labbook)}")
            # Currently, files will likely have the same owner and group they had in the host OS
            self._client.api.put_archive(self.image_tag, dst_dir, tarred_secret_file)
        finally:
            # Make sure the temporary Tar archive gets deleted.
            tarred_secret_file.close()

    # Utility methods

    def get_gigantum_client_ip(self) -> Optional[str]:
        """Method to get the monitored lab book container's IP address on the Docker bridge network

        Returns:
            str of IP address
        """
        clist: List[Container] = [c for c in self._client.containers.list()
                                  if 'gigantum.labmanager' in c.name
                                  # This catches the client container name during development w/ docker-compose
                                  or 'developer_labmanager' in c.name
                                  and 'gmlb-' not in c.name]
        if len(clist) != 1:
            raise ContainerException("Cannot find distinct Gigantum Client Labmanager container")

        return self.query_container_ip(clist[0].id)

    def _get_container(self, container_name: Optional[str] = None) -> Optional[Container]:
        """Get a Container object, defaulting to the container for this Project.

        If you don't need to provide flexibility regarding the target container, just use self.query_container()
        and use the value in self._container.

        Args:
            container_name: anything that will be recognized by docker.containers.get()
        """
        if not container_name:
            if self._container:
                try:
                    self._container.reload()
                    return self._container
                except docker.errors.NotFound:
                    self._container = None

            try:
                self._container = self._client.containers.get(self.image_tag)
            except docker.errors.NotFound:
                return None
            except docker.errors.NullResource:
                raise ContainerException('No path, labbook, or override_image_name given at init. '
                                         'Explicit container_name required.')
            return self._container
        else:
            try:
                return self._client.containers.get(container_name)
            except docker.errors.NotFound:
                return None

    def open_ports(self, port_list: List[int]) -> None:
        """A method to dynamically open ports to a running container. Locally this isn't really needed, but in the hub
        it is required

        Args:
            port_list: list of ports to open

        Returns:
            None
        """
        # This is a noop locally
        pass

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
        if dev_tool == "jupyterlab" or dev_tool == "notebook":
            # No configuration needed for jupyter locally
            pass
        elif dev_tool == "rstudio":
            # No configuration needed for rstudio locally
            pass
        else:
            raise ValueError(f"Unsupported development tool type '{dev_tool}' when trying to configure pre-launch.")


def get_docker_client(check_server_version=True, fallback=True) -> DockerClient:
    """Return a docker client with proper version to match server API. """

    if check_server_version:
        try:
            docker_server_api_version = _get_docker_server_api_version()
            return from_env(version=docker_server_api_version)
        except ValueError as e:
            if fallback:
                logger.warning("Could not determine Docker server API version; using default")
                return from_env()
            else:
                logger.error()
                raise e
    else:
        return from_env()


def _get_docker_server_api_version() -> str:
    """Retrieve the Docker server API version. """

    socket_path = '/var/run/docker.sock'
    if not os.path.exists(socket_path):
        raise ValueError('No docker.sock on machine (is a Docker server installed?)')

    socket_connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    socket_connection.connect(socket_path)
    socket_connection.send(b'GET http://*/version HTTP/1.1\r\nHost: *\r\n\r\n')

    response_data = socket_connection.recv(4000)
    content_lines = response_data.decode().split('\r\n')

    version_dict = json.loads(content_lines[-1])
    if 'ApiVersion' not in version_dict.keys():
        raise ValueError('ApiVersion not in Docker version config data')
    else:
        return version_dict['ApiVersion']
