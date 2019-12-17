import os

import tempfile
import git
import shutil

from gtmcore.imagebuilder import ImageBuilder
from gtmcore.environment import ComponentManager, RepositoryManager
from gtmcore.fixtures import labbook_dir_tree, mock_config_file, setup_index, mock_config_with_repo, mock_labbook, \
    ENV_UNIT_TEST_BASE, ENV_UNIT_TEST_REPO, ENV_UNIT_TEST_REV, mock_enabled_iframes
from gtmcore.environment.bundledapp import BundledAppManager

import gtmcore.fixtures


def populate_with_pkgs(lb):
    with tempfile.TemporaryDirectory() as checkoutdir:
        repo = git.Repo.clone_from("https://github.com/gigantum/base-images-testing.git", checkoutdir)
        shutil.copy(os.path.join(checkoutdir, "quickstart-jupyterlab/quickstart-jupyterlab_r0.yaml"),
                    os.path.join(lb.root_dir, ".gigantum", "env", "base"))


class TestImageBuilder(object):

    def test_temp_labbook_dir(self, mock_labbook):
        """Make sure that the labbook_dir_tree is created properly and loads into the ImageBuilder. """
        lb = mock_labbook[2]
        ib = ImageBuilder(lb)

    def test_load_baseimage(self, mock_labbook):
        """Ensure the FROM line exists in the _load_baseimage function. """
        lb = mock_labbook[2]
        populate_with_pkgs(lb)
        ib = ImageBuilder(lb)
        docker_lines = ib._load_baseimage()
        assert any(["FROM gigdev/gm-quickstart" in l for l in docker_lines])

    def test_load_baseimage_only_from(self, mock_labbook):
        """Ensure that _load_baseimage ONLY sets the FROM line, all others are comments or empty"""
        lb = mock_labbook[2]
        populate_with_pkgs(lb)
        ib = ImageBuilder(lb)
        assert len([l for l in ib._load_baseimage() if len(l) > 0 and l[0] != '#']) == 1

    def test_package_apt(self, mock_labbook):
        lb = mock_labbook[2]
        package_manager_dir = os.path.join(lb.root_dir, '.gigantum', 'env', 'package_manager')
        with open(os.path.join(package_manager_dir, 'apt_docker.yaml'), 'w') as apt_dep:
            content = os.linesep.join([
                'manager: apt',
                'package: docker',
                'version: 1.2.3',
                'from_base: false'
            ])
            apt_dep.write(content)

        ib = ImageBuilder(lb)
        pkg_lines = [l for l in ib._load_packages() if 'RUN' in l]
        assert 'RUN apt-get -y --no-install-recommends install docker' in pkg_lines

    def test_package_pip(self, mock_labbook):
        lb = mock_labbook[2]
        package_manager_dir = os.path.join(lb.root_dir, '.gigantum', 'env', 'package_manager')
        with open(os.path.join(package_manager_dir, 'pip3_docker.yaml'), 'w') as apt_dep:
            content = os.linesep.join([
                'manager: pip3',
                'package: docker',
                'version: "2.0.1"',
                'from_base: false'
            ])
            apt_dep.write(content)

        ib = ImageBuilder(lb)
        pkg_lines = [l for l in ib._load_packages() if 'RUN' in l]
        assert 'RUN pip install docker==2.0.1' in pkg_lines

        with open(os.path.join(package_manager_dir, 'pip3_docker.yaml'), 'w') as apt_dep:
            content = os.linesep.join([
                'manager: pip',
                'package: docker',
                'version: "2.0.1"',
                'from_base: true'
            ])
            apt_dep.write(content)

        ib = ImageBuilder(lb)
        pkg_lines = [l for l in ib._load_packages() if 'RUN' in l]
        assert 'RUN pip install docker==2.0.1' not in pkg_lines

    def test_validate_dockerfile(self, mock_labbook):
        """Test if the Dockerfile builds and can launch the image. """
        lb = mock_labbook[2]
        populate_with_pkgs(lb)
        package_manager_dir = os.path.join(lb.root_dir, '.gigantum', 'env', 'package_manager')
        with open(os.path.join(package_manager_dir, 'pip3_docker.yaml'), 'w') as apt_dep:
            content = os.linesep.join([
                'manager: pip3',
                'package: docker',
                'version: 2.0.1',
                'from_base: false'
            ])
            apt_dep.write(content)

        with open(os.path.join(package_manager_dir, 'apt_docker.yaml'), 'w') as apt_dep:
            content = os.linesep.join([
                'manager: apt',
                'package: docker',
                'version: 1.2.3',
                'from_base: false'
            ])
            apt_dep.write(content)

        with open(os.path.join(package_manager_dir, 'pip3_requests.yaml'), 'w') as apt_dep:
            content = os.linesep.join([
                'manager: pip3',
                'package: requests',
                'version: "2.18.4"',
                'from_base: false'
            ])
            apt_dep.write(content)

        ib = ImageBuilder(lb)
        n = ib.assemble_dockerfile(write=False)
        with open(os.path.join(lb.root_dir, ".gigantum", "env", "Dockerfile"), "w") as dockerfile:
            dockerfile_text = ib.assemble_dockerfile(write=False)
            dockerfile.write(dockerfile_text)

        test_lines = ['## Adding individual packages',
                      'RUN apt-get -y --no-install-recommends install docker',
                      'RUN pip install docker==2.0.1',
                      'RUN pip install requests==2.18.4']

        for line in test_lines:
            assert line in dockerfile_text.split(os.linesep)

    def test_docker_snippet(self, mock_labbook):
        lb = mock_labbook[2]
        package_manager_dir = os.path.join(lb.root_dir, '.gigantum', 'env', 'custom')
        erm = RepositoryManager(mock_labbook[0])
        erm.update_repositories()
        erm.index_repositories()
        cm = ComponentManager(lb)
        custom = ['RUN true', 'RUN touch /tmp/cat', 'RUN rm /tmp/cat']
        cm.add_base(ENV_UNIT_TEST_REPO, ENV_UNIT_TEST_BASE, ENV_UNIT_TEST_REV)
        cm.add_packages("pip", [{"manager": "pip", "package": "requests", "version": "2.18.4"}])
        cm.add_docker_snippet('test-docker', custom, description="Apostrophe's and wėįrd çhårāčtêrś")
        ib = ImageBuilder(lb)
        l = ib.assemble_dockerfile()
        assert all([any([i in l for i in custom]) for n in custom])

    def test_bundled_app_lines(self, mock_labbook):
        """Test if the Dockerfile builds with bundled app ports"""
        lb = mock_labbook[2]
        bam = BundledAppManager(lb)
        bam.add_bundled_app(8050, 'dash 1', 'a demo dash app 1', 'python app1.py')
        bam.add_bundled_app(9000, 'dash 2', 'a demo dash app 2', 'python app2.py')
        bam.add_bundled_app(9001, 'dash 3', 'a demo dash app 3', 'python app3.py')

        erm = RepositoryManager(mock_labbook[0])
        erm.update_repositories()
        erm.index_repositories()
        cm = ComponentManager(lb)
        cm.add_base(ENV_UNIT_TEST_REPO, ENV_UNIT_TEST_BASE, ENV_UNIT_TEST_REV)
        cm.add_packages("pip", [{"manager": "pip", "package": "requests", "version": "2.18.4"}])

        ib = ImageBuilder(lb)
        dockerfile_text = ib.assemble_dockerfile(write=False)
        test_lines = ['# Bundled Application Ports',
                      'EXPOSE 8050',
                      'EXPOSE 9000',
                      'EXPOSE 9001']

        docker_lines = dockerfile_text.split(os.linesep)
        for line in test_lines:
            assert line in docker_lines

    def test_iframe_support(self, mock_enabled_iframes):
        """Test if the Dockerfile builds with iframe support when enabled"""
        lb = mock_enabled_iframes[2]
        erm = RepositoryManager(mock_enabled_iframes[0])
        erm.update_repositories()
        erm.index_repositories()
        cm = ComponentManager(lb)
        cm.add_base('gigantum_base-images', 'rstudio-server', 1)

        ib = ImageBuilder(lb)
        dockerfile_text = ib.assemble_dockerfile(write=False)
        test_lines = ["# Enable IFrame support in JupyterLab/Jupyter Notebook",
                      "RUN mkdir -p /etc/jupyter/custom/",
                      "# Enable IFrame support in RStudio",
                      'RUN echo "\\n#Enable IFrames\\nwww-frame-origin=gigantum.com\\n" >> /etc/rstudio/rserver.conf']

        docker_lines = dockerfile_text.split(os.linesep)
        for line in test_lines:
            assert line in docker_lines

    def test_install_user_defined_ca(self, mock_labbook):
        """Test if the Dockerfile builds with user defined cas when cert files are available"""
        lb = mock_labbook[2]

        erm = RepositoryManager(mock_labbook[0])
        erm.update_repositories()
        erm.index_repositories()
        cm = ComponentManager(lb)
        cm.add_base(ENV_UNIT_TEST_REPO, ENV_UNIT_TEST_BASE, ENV_UNIT_TEST_REV)

        # No files in certificate dir, CA code shouldn't run
        test_lines = ["# Configure user provided CA certificates",
                      "RUN update-ca-certificates",
                      "ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt "
                      "SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt"]

        # No files in the certificate dir, CA code shouldn't run
        ib = ImageBuilder(lb)
        dockerfile_text = ib.assemble_dockerfile(write=False)
        docker_lines = dockerfile_text.split(os.linesep)
        for line in test_lines:
            assert line not in docker_lines

        # A file without a .crt extension in certificate dir, CA code still shouldn't run
        certificate_dir_container = os.path.join(lb.client_config.config['git']['working_directory'], 'certificates')
        os.makedirs(certificate_dir_container, exist_ok=True)
        with open(os.path.join(certificate_dir_container, 'test.txt'), 'wt') as tf:
            tf.write("dummy file")

        dockerfile_text = ib.assemble_dockerfile(write=False)
        docker_lines = dockerfile_text.split(os.linesep)
        for line in test_lines:
            assert line not in docker_lines

        # A file WITH a .crt extension in certificate dir, CA code SHOULD run
        certificate_dir_container = os.path.join(lb.client_config.config['git']['working_directory'], 'certificates')
        with open(os.path.join(certificate_dir_container, 'myCA.crt'), 'wt') as tf:
            tf.write("a faked CA file")

        dockerfile_text = ib.assemble_dockerfile(write=False)
        docker_lines = dockerfile_text.split(os.linesep)
        for line in test_lines:
            assert line in docker_lines
