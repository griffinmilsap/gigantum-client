import datetime
import functools
import glob
import shutil
import os
from string import Template

import yaml
from gtmcore.environment.componentmanager import ComponentManager
from typing import (Any, Dict, List)

from gtmcore.labbook import LabBook
from gtmcore.logging import LMLogger
from gtmcore.environment.utils import get_package_manager
from gtmcore.mitmproxy.mitmproxy import CURRENT_MITMPROXY_TAG
from gtmcore.environment.bundledapp import BundledAppManager


logger = LMLogger.get_logger()


class ImageBuilder(object):
    """Class to ingest indexes describing base images, environments, and dependencies into Dockerfiles. """

    def __init__(self, labbook: LabBook) -> None:
        """Create a new image builder given the path to labbook.

        Args:
            labbook: Subject LabBook
        """
        self.labbook = labbook
        if not os.path.exists(self.labbook.root_dir):
            raise IOError("Labbook directory {} does not exist.".format(self.labbook.root_dir))
        self._validate_labbook_tree()

    def _get_yaml_files(self, directory: str) -> List[str]:
        """Method to get all YAML files in a directory

        Args:
            directory(str): Directory to search

        Returns:
            list
        """
        return [x for x in glob.glob("{}{}*.yaml".format(directory, os.path.sep))]

    def _validate_labbook_tree(self) -> None:
        """Throw exception if labbook directory structure not in expected format. """
        subdirs = [['.gigantum'],
                   ['.gigantum', 'env'],
                   ['.gigantum', 'env', 'base'],
                   ['.gigantum', 'env', 'custom'],
                   ['.gigantum', 'env', 'package_manager']]

        for subdir in subdirs:
            if not os.path.exists(os.path.join(self.labbook.root_dir, *subdir)):
                raise ValueError("Labbook directory missing subdir `{}'".format(subdir))

    def _extra_base_images(self) -> List[str]:
        """Add other needed images via multi-stage build"""
        docker_lines = []
        cm = ComponentManager(self.labbook)
        if 'rstudio' in cm.base_fields['development_tools']:
                docker_lines.append("FROM gigantum/mitmproxy_proxy:" + CURRENT_MITMPROXY_TAG)

        return docker_lines

    def _import_baseimage_fields(self) -> Dict[str, Any]:
        """Load fields from base_image yaml file into a convenient dict. """
        root_dir = os.path.join(self.labbook.root_dir, '.gigantum', 'env', 'base')
        base_images = self._get_yaml_files(root_dir)

        logger.debug("Searching {} for base image file".format(root_dir))
        if len(base_images) != 1:
            raise ValueError(f"There should only be one base image in {root_dir}, found {len(base_images)}")

        logger.info("Using {} as base image file for labbook at {}.".format(base_images[0], self.labbook.root_dir))
        with open(base_images[0]) as base_image_file:
            fields = yaml.safe_load(base_image_file)

        return fields

    def _load_baseimage(self) -> List[str]:
        """Search expected directory structure to find the base image. Only one should exist. """

        fields = self._import_baseimage_fields()
        generation_ts = str(datetime.datetime.now())
        docker_owner_ns = fields['image']['namespace']
        docker_repo = fields['image']['repository']
        docker_tag = fields['image']['tag']

        docker_lines: List[str] = list()
        docker_lines.append("# Dockerfile generated on {}".format(generation_ts))
        docker_lines.append("# Name: {}".format(fields["name"]))
        docker_lines.append("# Description: {}".format(fields["description"]))
        docker_lines.append("")
        
        # Must remove '_' if its in docker hub namespace.
        prefix = '' if '_' in docker_owner_ns else f'{docker_owner_ns}/'
        docker_lines.append("FROM {}{}:{}".format(prefix, docker_repo, docker_tag))

        return docker_lines

    def _enable_iframes(self) -> List[str]:
        """Step to add layers to enable iframe support, only if iframe support is enabled in the config"""
        docker_lines: List[str] = list()
        # Only perform this step if iframe support is enabled
        if self.labbook.client_config.config['environment']['iframe']['enabled'] is True:
            # Get dev tools in this project
            fields = self._import_baseimage_fields()
            tools = fields['development_tools']

            # Get the allowed origin from the config file
            allowed_origin = self.labbook.client_config.config['environment']['iframe']['allowed_origin']

            if "jupyterlab" in tools or "notebook" in tools:
                # Create notebook config file to allow iframes
                docker_lines.append("# Enable IFrame support in JupyterLab/Jupyter Notebook")
                docker_lines.append("RUN mkdir -p /etc/jupyter/custom/")

                notebook_config_template = Template("RUN echo \"c.NotebookApp.tornado_settings = {'headers': {'Content-Security-Policy': \\\"frame-ancestors $allowed_origin 'self'; report-uri /api/security/csp-report\\\"}}\" >> /etc/jupyter/jupyter_notebook_config.py")
                notebook_config_str = notebook_config_template.substitute(allowed_origin=allowed_origin)
                docker_lines.append(notebook_config_str)

            if "rstudio" in tools:
                docker_lines.append("# Enable IFrame support in RStudio")
                docker_lines.append(f'RUN echo "\\n#Enable IFrames\\nwww-frame-origin={allowed_origin}\\n" >>'
                                    f' /etc/rstudio/rserver.conf')
                docker_lines.append("")

        return docker_lines

    def _install_user_defined_ca(self) -> List[str]:
        """Step to add layers to install user defined CA certificates into Project containers"""
        docker_lines: List[str] = list()
        certificate_dir_client = os.path.join(self.labbook.client_config.config['git']['working_directory'],
                                              'certificates')
        certificate_files = [x for x in glob.glob(os.path.join(certificate_dir_client, "*.crt"))]

        # Only perform this step if there are .crt files in the `certificates` dir in the root of the working dir
        if certificate_files:
            # Copy certificates into an untracked directory within the container build context
            project_build_context = os.path.join(self.labbook.root_dir, '.gigantum', 'env', 'certificates')
            os.makedirs(project_build_context, exist_ok=True)
            for filename in certificate_files:
                shutil.copy(filename, project_build_context)

            # Render Dockerfile contents
            docker_lines.append("# Configure user provided CA certificates")
            docker_lines.append(f"COPY certificates/*.crt /usr/local/share/ca-certificates/")
            docker_lines.append(f"RUN update-ca-certificates")
            docker_lines.append(f"ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt "
                                f"SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt")
            docker_lines.append("")

        return docker_lines

    def _load_packages(self) -> List[str]:
        """Load packages from yaml files in expected location in directory tree. """
        root_dir = os.path.join(self.labbook.root_dir, '.gigantum', 'env', 'package_manager')
        package_files = [os.path.join(root_dir, n) for n in os.listdir(root_dir) if 'yaml' in n]
        docker_lines = ['## Adding individual packages']
        apt_updated = False

        for package in sorted(package_files):
            pkg_fields: Dict[str, Any] = {}

            with open(package) as package_content:
                pkg_fields.update(yaml.safe_load(package_content))

            # Generate the appropriate docker command for the given package info
            pkg_info = {"name": str(pkg_fields['package']),
                        "version": str(pkg_fields.get('version'))}
            if not pkg_fields.get('from_base'):
                if pkg_fields['manager'] == 'apt' and not apt_updated:
                    docker_lines.append('RUN apt-get -y update')
                    apt_updated = True

                docker_lines.extend(
                    get_package_manager(pkg_fields['manager']).generate_docker_install_snippet([pkg_info]))

        return docker_lines

    def _load_docker_snippets(self) -> List[str]:
        docker_lines = ['# Custom docker snippets']
        root_dir = os.path.join(self.labbook.root_dir, '.gigantum', 'env', 'docker')
        if not os.path.exists(root_dir):
            logger.warning(f"No `docker` subdirectory for environment in labbook")
            return []

        for snippet_file in [f for f in os.listdir(root_dir) if '.yaml' in f]:
            docker_data = yaml.safe_load(open(os.path.join(root_dir, snippet_file)))
            docker_lines.append(f'# Custom Docker: {docker_data["name"]} - {len(docker_data["content"])}'
                                f'line(s) - (Created {docker_data["timestamp_utc"]})')
            docker_lines.extend(docker_data['content'])
        return docker_lines

    def _load_bundled_apps(self) -> List[str]:
        """Method to get the bundled apps docker snippets

        Returns:
            List
        """
        docker_lines = ['# Bundled Application Ports']
        bam = BundledAppManager(self.labbook)
        docker_lines.extend(bam.get_docker_lines())
        return docker_lines

    def _post_image_hook(self) -> List[str]:
        """Contents that must be after baseimages but before development environments. """
        docker_lines = ["# Post-image creation hooks",
                        'COPY entrypoint.sh /usr/local/bin/entrypoint.sh',
                        'RUN chmod u+x /usr/local/bin/entrypoint.sh',
                        '']
        return docker_lines

    def _entrypoint_hooks(self):
        """ Contents of docker setup that must be at end of Dockerfile. """

        env_vars = "ENV LB_HOME=/mnt/labbook"
        env_vars = f"{env_vars} PROJECT_ROOT=/mnt/labbook"
        env_vars = f"{env_vars} PROJECT_CODE=/mnt/labbook/code"
        env_vars = f"{env_vars} PROJECT_INPUT=/mnt/labbook/input"
        env_vars = f"{env_vars} PROJECT_OUTPUT=/mnt/labbook/output"

        return [
            '## Entrypoint hooks',
            env_vars,
            "# Run Environment",
            'ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]',
            'WORKDIR /mnt/labbook',
            '',
            '# Use this command to make the container run indefinitely',
            'CMD ["tail", "-f", "/dev/null"]',
            '']

    def assemble_dockerfile(self, write: bool = True) -> str:
        """Create the content of a Dockerfile per the fields in the indexed data.

        Returns:
            str - Content of Dockerfile in single string using os.linesep as line separator.
        """
        assembly_pipeline = [self._extra_base_images,
                             self._load_baseimage,
                             self._install_user_defined_ca,
                             self._load_packages,
                             self._load_docker_snippets,
                             self._load_bundled_apps,
                             self._enable_iframes,
                             self._post_image_hook,
                             self._entrypoint_hooks]

        # flat map the results of executing the pipeline.
        try:
            docker_lines: List[str] = functools.reduce(lambda a, b: a + b, [f() for f in assembly_pipeline], [])
        except KeyError as e:
            logger.error('Component file missing key: {}'.format(e))
            raise
        except Exception as e:
            logger.error(e)
            raise

        dockerfile_name = os.path.join(self.labbook.root_dir, ".gigantum", "env", "Dockerfile")
        if write:
            logger.info("Writing Dockerfile to {}".format(dockerfile_name))
            with open(dockerfile_name, "w") as dockerfile:
                dockerfile.write('\n'.join(docker_lines))
        else:
            logger.info("Dockerfile NOT being written; write=False; {}".format(dockerfile_name))

        return os.linesep.join(docker_lines)
