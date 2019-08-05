import os
from datetime import datetime
import sys

from git import Repo
import docker
from docker.errors import NotFound
import yaml

from gtm.common import get_client_root, get_resources_root


class CircleCIImageBuilder(object):
    """Class to manage building base images"""

    def _get_current_commit_hash(self) -> str:
        """Method to get the current commit hash of the gtm repository

        Returns:
            str
        """
        # Get the path of the root directory
        repo = Repo(get_client_root())
        return repo.head.commit.hexsha

    def _generate_image_tag_suffix(self) -> str:
        """Method to generate a suffix for an image tag

        Returns:
            str
        """
        return "{}-{}".format(self._get_current_commit_hash()[:10], str(datetime.utcnow().date()))

    def _generate_config_file(self) -> None:
        """

        Returns:

        """
        # Write updated config file
        base_config_file = os.path.join(get_client_root(), "packages", 'gtmcore', 'gtmcore',
                                        'configuration', 'config', 'labmanager.yaml.default')
        output_dir = os.path.join(get_client_root(), "build", 'circleci')

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        with open(base_config_file, "rt") as cf:
            base_data = yaml.load(cf)

        # Add Build Info
        built_on = str(datetime.utcnow())
        revision = self._get_current_commit_hash()[:8]
        base_data['build_info'] = f'Gigantum Client :: {built_on} :: {revision}'

        # Write out updated config file
        with open(os.path.join(output_dir, 'labmanager.yaml'), "wt") as cf:
            cf.write(yaml.dump(base_data, default_flow_style=False))

    def _build_image(self, verbose: bool=True, no_cache: bool=False) -> str:
        """

        Args:
            verbose(bool): set to True to print output
            no_cache(bool): set to True to ignore docker build cache

        Returns:

        """
        client = docker.from_env()

        base_tag = "gigantum/circleci-client"
        named_tag = "{}:{}".format(base_tag, self._generate_image_tag_suffix())

        docker_file = os.path.join(get_resources_root(), 'docker', 'Dockerfile_circleci')

        self._generate_config_file()

        if verbose:
            [print(ln[list(ln.keys())[0]], end='') for ln in client.api.build(path=get_client_root(),
                                                                              dockerfile=docker_file,
                                                                              tag=named_tag,
                                                                              nocache=no_cache,
                                                                              pull=True, rm=True,
                                                                              decode=True)]
        else:
            client.images.build(path=get_client_root(),  dockerfile=docker_file, tag=named_tag,
                                pull=True, nocache=no_cache)

        # Verify the desired image built successfully
        try:
            client.images.get(named_tag)
        except NotFound:
            raise ValueError("Image Build Failed!")

        return named_tag

    def _publish_image(self, image_tag: str, verbose=True) -> None:
        """Private method to push images to the logged in server (e.g hub.docker.com)

        Args:
            image_tag(str): full image tag to publish

        Returns:
            None
        """
        client = docker.from_env()

        # Split out the image and the tag
        image, tag = image_tag.split(":")

        if verbose:
            last_msg = ""
            for ln in client.api.push(image, tag=tag, stream=True, decode=True):
                if 'status' in ln:
                    if last_msg != ln.get('status'):
                        print(f"\n{ln.get('status')}", end='', flush=True)
                        last_msg = ln.get('status')
                    else:
                        print(".", end='', flush=True)

                elif 'error' in ln:
                    sys.stderr.write(f"\n{ln.get('error')}\n")
                    sys.stderr.flush()
                else:
                    print(ln)
        else:
            client.images.push(image, tag=tag)

    def update(self, verbose=True, no_cache=False) -> None:
        """Method to circleCI container

        Args:
            verbose(bool): flag indication if output should print to the console
            no_cache(bool): flag indicating if the docker cache should be ignored

        Returns:
            None
        """
        # Build image
        print(f"\n** Building CircleCI Docker image")
        image_tag = self._build_image(verbose=verbose, no_cache=no_cache)

        # Publish to dockerhub
        print(f"\n\n** Publishing CircleCI Docker image to DockerHub: {image_tag}")
        self._publish_image(image_tag, verbose)

        print("Done!")
        print(f"\n\n** Update `.circleci/config.yml` to point to {image_tag} and "
              "commit to run tests with new container **")
