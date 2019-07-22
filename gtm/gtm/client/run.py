import os
import re
import platform
import subprocess

import docker

from gtm.utils import dockerize_windows_path, DockerVolume
from gtm.common.gpu import get_nvidia_driver_version


class ClientRunner(object):
    """Class to manage running the Gigantum client container
    """

    def __init__(self, image_name: str, container_name: str, show_output: bool=False):
        self.docker_client = docker.from_env()
        self.image_name = image_name
        self.container_name = container_name
        self.docker_image = self.docker_client.images.get(image_name)
        self.show_output = show_output

        if not self.docker_image:
            raise ValueError("Image name `{}' does not exist.".format(image_name))

    @property
    def is_running(self):
        """Return True if a container by given name exists with `docker ps -a`. """
        return any([container.name == self.container_name for container in self.docker_client.containers.list()])

    def stop(self, remove_all: bool=False):
        """Stop the the client container (or all containers) and prune"""
        if remove_all:
            # If all is set, we remove all containers!
            for container in self.docker_client.containers.list():
                container.stop()
                print("*** Stopped: {}".format(container.name))
        else:
            if not self.is_running:
                print("Gigantum client is not running. No containers stopped.")
                return

            containers = list(filter(lambda c: c.name == self.container_name, self.docker_client.containers.list()))
            assert len(containers) == 1
            containers[0].stop()
            print("*** Stopped: {}".format(containers[0].name))

        self.docker_client.containers.prune()

    def launch(self):
        """Launch the docker container. """
        working_dir = os.path.join(os.path.expanduser("~"), "gigantum")
        port_mapping = {'10000/tcp': 10000,
                        '10001/tcp': 10001,
                        '10002/tcp': 10002}

        # Make sure the container-container share volume exists
        share_volume = DockerVolume("labmanager_share_vol")
        if not share_volume.exists():
            share_volume.create()

        volume_mapping = dict()
        volume_mapping['labmanager_share_vol'] = {'bind': '/mnt/share', 'mode': 'rw'}
        volume_mapping['/var/run/docker.sock'] = {'bind': '/var/run/docker.sock', 'mode': 'rw'}

        environment_mapping = dict()
        if platform.system() == 'Windows':
            # HOST_WORK_DIR will be used to mount inside labbook.
            environment_mapping['HOST_WORK_DIR'] = dockerize_windows_path(working_dir)
            environment_mapping['WINDOWS_HOST'] = 1
            # Windows does not support cached, but this is silently ignored (as of late Jan 2018)
            # We convert \ to /
            volume_mapping[dockerize_windows_path(working_dir)] = {'bind': '/mnt/gigantum', 'mode': 'cached'}
        else:
            environment_mapping['HOST_WORK_DIR'] = working_dir
            environment_mapping['LOCAL_USER_ID'] = os.getuid()
            volume_mapping[working_dir] = {'bind': '/mnt/gigantum', 'mode': 'cached'}

        # get the nvidia driver if available on the host
        nvidia_driver_version = get_nvidia_driver_version()
        if nvidia_driver_version:
            environment_mapping['NVIDIA_DRIVER_VERSION'] = nvidia_driver_version

        self.docker_client.containers.run(image=self.docker_image,
                                          detach=True,
                                          name=self.container_name,
                                          init=True,
                                          ports=port_mapping,
                                          volumes=volume_mapping,
                                          environment=environment_mapping)
