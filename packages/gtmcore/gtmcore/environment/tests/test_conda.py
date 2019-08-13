import os
import pytest

from gtmcore.fixtures.container import mock_config_with_repo, build_lb_image_for_env_conda
from gtmcore.environment.conda import Conda3PackageManager, Conda2PackageManager

from gtmcore.environment.tests import ENV_SKIP_MSG, ENV_SKIP_TEST


@pytest.mark.skipif(ENV_SKIP_TEST, reason=ENV_SKIP_MSG)
class TestConda3PackageManager(object):
    def test_search(self, build_lb_image_for_env_conda):
        """Test search command"""
        mrg = Conda3PackageManager()
        lb = build_lb_image_for_env_conda[0]
        username = build_lb_image_for_env_conda[1]
        result = mrg.search("reque*", lb, username)
        assert type(result) == list
        assert type(result[0]) == str
        assert len(result) > 6
        assert "requests" in result
        result = mrg.search("nump*", lb, username)
        assert type(result) == list
        assert type(result[0]) == str
        assert len(result) > 2
        assert "numpy" in result

    def test_search_no_wildcard(self, build_lb_image_for_env_conda):
        """Test search command"""
        mrg = Conda3PackageManager()
        lb = build_lb_image_for_env_conda[0]
        username = build_lb_image_for_env_conda[1]
        result = mrg.search("reque", lb, username)
        assert type(result) == list
        assert type(result[0]) == str
        assert len(result) > 6
        assert "requests" in result

    def test_search_empty(self, build_lb_image_for_env_conda):
        """Test search command with no result"""
        mrg = Conda3PackageManager()
        lb = build_lb_image_for_env_conda[0]
        username = build_lb_image_for_env_conda[1]
        result = mrg.search("asdffdghdfghdraertasdfsadfa", lb, username)
        assert type(result) == list
        assert len(result) == 0

    def test_list_versions(self, build_lb_image_for_env_conda):
        """Test list_versions command"""
        mrg = Conda3PackageManager()
        lb = build_lb_image_for_env_conda[0]
        username = build_lb_image_for_env_conda[1]
        result = mrg.list_versions("python-coveralls", lb, username)
        assert len(result) > 6
        # We use negative indexing here because the list is sorted newest to oldest
        # New versions may be added at the beginning, but if we count from the end,
        # hopefully that's stable
        assert result[-2] == "2.6.0"
        assert result[-5] == "2.9.1"
        assert result[-6] == "2.9.2"

    def test_list_installed_packages(self, build_lb_image_for_env_conda):
        """Test list_installed_packages command

        Note, if the contents of the container change, this test will break and need to be updated. Because of this,
        only limited asserts are made to make sure things are coming back in a reasonable format
        """
        mrg = Conda3PackageManager()
        lb = build_lb_image_for_env_conda[0]
        username = build_lb_image_for_env_conda[1]
        result = mrg.list_installed_packages(lb, username)

        assert type(result) == list
        assert len(result) >= 14
        assert type(result[0]) == dict
        assert type(result[0]['name']) == str
        assert type(result[0]['version']) == str

    def test_generate_docker_install_snippet_single(self):
        """Test generate_docker_install_snippet command
        """
        mrg = Conda3PackageManager()
        packages = [{'name': 'mypackage', 'version': '3.1.4'}]

        result = mrg.generate_docker_install_snippet(packages)
        assert result == ['RUN conda install -yq mypackage=3.1.4']

        result = mrg.generate_docker_install_snippet(packages, single_line=True)
        assert result == ['RUN conda install -yq mypackage=3.1.4']

    def test_generate_docker_install_snippet_multiple(self):
        """Test generate_docker_install_snippet command
        """
        mrg = Conda3PackageManager()
        packages = [{'name': 'mypackage', 'version': '3.1.4'},
                    {'name': 'yourpackage', 'version': '2017-54.0'}]

        result = mrg.generate_docker_install_snippet(packages)
        assert result == ['RUN conda install -yq mypackage=3.1.4 yourpackage=2017-54.0']

        result = mrg.generate_docker_install_snippet(packages, single_line=True)
        assert result == ['RUN conda install -yq mypackage=3.1.4 yourpackage=2017-54.0']

    def test_list_versions_badpackage(self, build_lb_image_for_env_conda):
        """Test list_versions command"""
        mrg = Conda3PackageManager()
        lb = build_lb_image_for_env_conda[0]
        username = build_lb_image_for_env_conda[1]
        with pytest.raises(ValueError):
            mrg.list_versions("gigantumasdfasdfasdf", lb, username)

    def test_is_valid_errors(self, build_lb_image_for_env_conda):
        """Test list_versions command"""
        pkgs = [{"manager": "conda3", "package": "numpy", "version": "1.14.2"},
                {"manager": "conda3", "package": "plotly", "version": "100.00"},
                {"manager": "conda3", "package": "cdutil", "version": ""},
                {"manager": "conda3", "package": "asdfasdfasdf", "version": ""}]

        mrg = Conda3PackageManager()
        lb = build_lb_image_for_env_conda[0]
        username = build_lb_image_for_env_conda[1]
        result = mrg.validate_packages(pkgs, lb, username)

        assert result[0].package == "numpy"
        assert result[0].version == "1.14.2"
        assert result[0].error is False

        assert result[1].package == "plotly"
        assert result[1].version == "100.00"
        assert result[1].error is True

        assert result[2].package == "cdutil"
        assert result[2].version == "8.1"
        assert result[2].error is False

        assert result[3].package == "asdfasdfasdf"
        assert result[3].version == ""
        assert result[3].error is True

    def test_is_valid_good(self, build_lb_image_for_env_conda):
        """Test valid packages command"""
        pkgs = [{"manager": "conda3", "package": "nltk", "version": "3.2.2"},
                {"manager": "conda3", "package": "cdutil", "version": ""}]

        mrg = Conda3PackageManager()
        lb = build_lb_image_for_env_conda[0]
        username = build_lb_image_for_env_conda[1]
        result = mrg.validate_packages(pkgs, lb, username)

        assert result[0].package == "nltk"
        assert result[0].version == "3.2.2"
        assert result[0].error is False

        assert result[1].package == "cdutil"
        assert result[1].version == "8.1"
        assert result[1].error is False

    def test_package_metadata(self, build_lb_image_for_env_conda):
        """Test getting package metadata"""
        mrg = Conda3PackageManager()
        lb = build_lb_image_for_env_conda[0]
        username = build_lb_image_for_env_conda[1]
        result = mrg.get_packages_metadata(['nltk', 'cdutil', 'numpy', 'sadfasfasf'], lb, username)

        assert len(result) == 4
        assert result[0].package == "nltk"
        assert result[0].description == 'Natural Language Toolkit'
        assert result[0].docs_url == 'http://www.nltk.org/'
        assert result[0].latest_version == '3.4.4'
        assert result[1].package == "cdutil"
        assert result[1].description == 'A set of tools to manipulate climate data'
        assert result[1].docs_url == 'http://anaconda.org/conda-forge/cdutil'
        assert result[1].latest_version == '8.1'
        assert result[2].package == "numpy"
        assert result[2].description == 'Array processing for numbers, strings, records, and objects.'
        assert result[2].docs_url == 'https://docs.scipy.org/doc/numpy/reference/'
        assert isinstance(result[2].docs_url, str) is True
        assert result[3].package == "sadfasfasf"
        assert result[3].description is None
        assert result[3].docs_url is None
        assert result[3].latest_version is None

    # *** CONDA2 PACKAGE MANAGER TESTS ***
    def test_is_valid_errors2(self, build_lb_image_for_env_conda):
        """Test list_versions command"""
        pkgs = [{"manager": "conda2", "package": "numpy", "version": "1.14.2"},
                {"manager": "conda2", "package": "plotly", "version": "100.00"},
                {"manager": "conda2", "package": "cdutil", "version": ""},
                {"manager": "conda2", "package": "asdfasdfasdf", "version": ""}]

        mrg = Conda2PackageManager()
        lb = build_lb_image_for_env_conda[0]
        username = build_lb_image_for_env_conda[1]
        result = mrg.validate_packages(pkgs, lb, username)

        assert result[0].package == "numpy"
        assert result[0].version == "1.14.2"
        assert result[0].error is False

        assert result[1].package == "plotly"
        assert result[1].version == "100.00"
        assert result[1].error is True

        assert result[2].package == "cdutil"
        assert result[2].version == "8.1"
        assert result[2].error is False

        assert result[3].package == "asdfasdfasdf"
        assert result[3].version == ""
        assert result[3].error is True

    def test_is_valid_good2(self, build_lb_image_for_env_conda):
        """Test valid packages command"""
        pkgs = [{"manager": "conda2", "package": "nltk", "version": "3.2.2"},
                {"manager": "conda2", "package": "cdutil", "version": ""}]

        mrg = Conda2PackageManager()
        lb = build_lb_image_for_env_conda[0]
        username = build_lb_image_for_env_conda[1]
        result = mrg.validate_packages(pkgs, lb, username)

        assert result[0].package == "nltk"
        assert result[0].version == "3.2.2"
        assert result[0].error is False

        assert result[1].package == "cdutil"
        assert result[1].version == "8.1"
        assert result[1].error is False
    # *** CONDA2 PACKAGE MANAGER TESTS ***
