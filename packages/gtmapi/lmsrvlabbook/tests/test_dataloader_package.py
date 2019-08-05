from gtmcore.environment.packagemanager import PackageMetadata

from lmsrvlabbook.tests.fixtures import fixture_working_dir, build_image_for_jupyterlab
from promise import Promise

from lmsrvlabbook.dataloader.package import PackageDataloader


class TestDataloaderPackage(object):
    def test_load_one_pip(self, build_image_for_jupyterlab):
        """Test loading 1 package"""

        key = "pip&gtmunit1"
        lb, username = build_image_for_jupyterlab[0], build_image_for_jupyterlab[5]

        loader = PackageDataloader([key], lb, username)
        promise1 = loader.load(key)
        assert isinstance(promise1, Promise)

        pkg = promise1.get()
        assert isinstance(pkg, PackageMetadata) is True
        assert pkg.description == 'Package 1 for Gigantum Client unit testing.'
        assert pkg.docs_url == 'https://github.com/gigantum/gigantum-client'
        assert pkg.latest_version == '0.12.4'

    def test_load_many_apt(self, build_image_for_jupyterlab):
        lb, username = build_image_for_jupyterlab[0], build_image_for_jupyterlab[5]
        keys = ["apt&curl", "apt&vim"]
        loader = PackageDataloader(keys, lb, username)
        promise1 = loader.load_many(keys)
        assert isinstance(promise1, Promise)

        version_list = promise1.get()
        assert len(version_list) == 2
        assert isinstance(version_list[0], PackageMetadata) is True
        assert 'ubuntu' in version_list[0].latest_version
        assert version_list[0].description == 'command line tool for transferring data with URL syntax'
        assert version_list[0].docs_url is None
        assert version_list[0].package == 'curl'
        assert version_list[0].package_manager == 'apt'

        assert 'ubuntu' in version_list[1].latest_version
        assert version_list[1].description == 'Vi IMproved - enhanced vi editor'
        assert version_list[1].docs_url is None
        assert version_list[1].package == 'vim'
        assert version_list[1].package_manager == 'apt'

    def test_load_many_pip(self, build_image_for_jupyterlab):
        """Test loading many labbooks"""
        lb, username = build_image_for_jupyterlab[0], build_image_for_jupyterlab[5]
        keys = ["pip&gtmunit1", "pip&gtmunit2", "pip&gtmunit3"]
        loader = PackageDataloader(keys, lb, username)
        promise1 = loader.load_many(keys)
        assert isinstance(promise1, Promise)

        version_list = promise1.get()
        assert len(version_list) == 3
        assert isinstance(version_list[0], PackageMetadata) is True
        # Note, all the gtmunit packages were pushed with the same description, so this is correct.
        assert version_list[0].latest_version == "0.12.4"
        assert version_list[0].description == 'Package 1 for Gigantum Client unit testing.'
        assert version_list[0].docs_url == 'https://github.com/gigantum/gigantum-client'
        assert version_list[1].latest_version == "12.2"
        assert version_list[1].description == 'Package 1 for Gigantum Client unit testing.'
        assert version_list[1].docs_url == 'https://github.com/gigantum/gigantum-client'
        assert version_list[2].latest_version == "5.0"
        assert version_list[2].description == 'Package 1 for Gigantum Client unit testing.'
        assert version_list[2].docs_url == 'https://github.com/gigantum/gigantum-client'

    def test_load_many_conda(self, build_image_for_jupyterlab):
        """Test loading many conda3 packages"""
        lb, username = build_image_for_jupyterlab[0], build_image_for_jupyterlab[5]
        keys = ["conda3&cdutil", "conda3&python-coveralls", "conda3&nltk", "conda3&asdfasdffghdfdasfgh"]
        loader = PackageDataloader(keys, lb, username)
        promise1 = loader.load_many(keys)
        assert isinstance(promise1, Promise)

        version_list = promise1.get()
        assert len(version_list) == 4

        assert version_list[0].latest_version == "8.1"
        assert version_list[0].description == 'A set of tools to manipulate climate data'
        assert version_list[0].docs_url == 'http://anaconda.org/conda-forge/cdutil'

        assert version_list[1].latest_version == "2.9.3"
        assert version_list[1].description == 'Python interface to coveralls.io API\\n'
        assert version_list[1].docs_url == 'http://anaconda.org/conda-forge/python-coveralls'

        assert version_list[2].latest_version == "3.2.5"
        assert version_list[2].description == 'Natural Language Toolkit'
        assert version_list[2].docs_url == 'http://www.nltk.org/'

        assert version_list[3].latest_version is None
        assert version_list[3].description is None
        assert version_list[3].docs_url is None

    def test_load_many_conda2(self, build_image_for_jupyterlab):
        """Test loading many conda2 packages"""
        lb, username = build_image_for_jupyterlab[0], build_image_for_jupyterlab[5]
        keys = ["conda2&cdutil", "conda2&python-coveralls", "conda2&nltk"]
        loader = PackageDataloader(keys, lb, username)
        promise1 = loader.load_many(keys)
        assert isinstance(promise1, Promise)

        version_list = promise1.get()
        assert len(version_list) == 3

        assert version_list[0].latest_version == "8.1"
        assert version_list[0].description == 'A set of tools to manipulate climate data'
        assert version_list[0].docs_url == 'http://anaconda.org/conda-forge/cdutil'

        assert version_list[1].latest_version == "2.9.3"
        assert version_list[1].description == 'Python interface to coveralls.io API\\n'
        assert version_list[1].docs_url == 'http://anaconda.org/conda-forge/python-coveralls'

        assert version_list[2].latest_version == "3.2.5"
        assert version_list[2].description == 'Natural Language Toolkit'
        assert version_list[2].docs_url == 'http://www.nltk.org/'

    def test_load_many_mixed(self, build_image_for_jupyterlab):
        """Test loading many labbooks"""
        lb, username = build_image_for_jupyterlab[0], build_image_for_jupyterlab[5]
        keys = ["conda3&cdutil", "pip&gtmunit1", "pip&gtmunit2", "conda3&nltk", 'apt&curl']
        loader = PackageDataloader(keys, lb, username)
        promise1 = loader.load_many(keys)
        assert isinstance(promise1, Promise)

        version_list = promise1.get()
        assert len(version_list) == 5
        assert version_list[0].latest_version == "8.1"
        assert version_list[0].description == 'A set of tools to manipulate climate data'
        assert version_list[0].docs_url == 'http://anaconda.org/conda-forge/cdutil'

        assert version_list[1].latest_version == '0.12.4'
        assert version_list[1].description == 'Package 1 for Gigantum Client unit testing.'
        assert version_list[1].docs_url == 'https://github.com/gigantum/gigantum-client'

        assert version_list[2].latest_version == '12.2'
        assert version_list[2].description == 'Package 1 for Gigantum Client unit testing.'
        assert version_list[2].docs_url == 'https://github.com/gigantum/gigantum-client'

        assert version_list[3].latest_version == '3.2.5'
        assert version_list[3].description == 'Natural Language Toolkit'
        assert version_list[3].docs_url == 'http://www.nltk.org/'

        assert version_list[4].latest_version is not None
        assert version_list[4].description == 'command line tool for transferring data with URL syntax'
        assert version_list[4].docs_url is None

