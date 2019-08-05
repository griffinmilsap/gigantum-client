# Copyright (c) 2017 FlashX, LLC
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
import json
import os
import shutil
import redis
import tempfile
import requests
import collections
import git
from pkg_resources import resource_filename
import pytest
import uuid

from gtmcore.configuration import Configuration
from gtmcore.environment import RepositoryManager
from gtmcore.inventory.inventory  import InventoryManager
from gtmcore.activity.detaildb import ActivityDetailDB
from gtmcore.activity import ActivityStore
from gtmcore.gitlib.git import GitAuthor
from gtmcore.files import FileOperations
from gtmcore.inventory.branching import BranchManager



ENV_UNIT_TEST_REPO = 'gigantum_base-images-testing'
ENV_UNIT_TEST_BASE = 'quickstart-jupyterlab'
ENV_UNIT_TEST_REV = 2


def flush_redis_repo_cache():
    r = redis.Redis(db=7)
    r.flushdb()


def _create_temp_work_dir(override_dict: dict = None, lfs_enabled: bool = True):
    """Helper method to create a temporary working directory and associated config file"""
    def merge_dict(d1, d2) -> None:
        """Method to merge 1 dictionary into another, updating and adding key/values as needed
        """
        for k, v2 in d2.items():
            v1 = d1.get(k)  # returns None if v1 has no value for this key
            if (isinstance(v1, collections.Mapping) and
                    isinstance(v2, collections.Mapping)):
                merge_dict(v1, v2)
            else:
                d1[k] = v2

    # Create a temporary working directory
    unit_test_working_dir = os.path.join(tempfile.gettempdir(), uuid.uuid4().hex)
    os.makedirs(unit_test_working_dir)
    os.makedirs(os.path.join(unit_test_working_dir, '.labmanager', 'upload'), exist_ok=True)

    default_override_config = {
        'core': {
            'team_mode': False,
            'import_demo_on_first_login': False
        },
        'environment': {
            'repo_url': ["https://github.com/gigantum/base-images-testing.git"]
        },
        'flask': {
            'DEBUG': False
        },
        'git': {
            'working_directory': unit_test_working_dir,
            'backend': 'filesystem-shim',
            'lfs_enabled': lfs_enabled
        },
        'auth': {
            'audience': "io.gigantum.api.dev"
        },
        'lock': {
            'redis': {
                'strict': False,
            }
        }
    }

    os.environ['HOST_WORK_DIR'] = unit_test_working_dir

    config = Configuration()
    merge_dict(config.config, default_override_config)
    if override_dict:
        config.config.update(override_dict)

    config_file = os.path.join(unit_test_working_dir, "temp_config.yaml")
    config.save(config_file)

    # Return (path-to-config-file, ephemeral-working-directory).
    return config_file, unit_test_working_dir


def _MOCK_create_remote_repo2(repository, username: str, visibility, access_token = None) -> None:
    """ Used to mock out creating a Labbook remote Gitlab repo. This is not a fixture per se,

    Usage:

    ```
        @mock.patch('gtmcore.labbook.LabBook._create_remote_repo', new=_MOCK_create_remote_repo)
        def my_test_(...):
            ...
    ```
    """
    rand = str(uuid.uuid4())[:6]
    working_dir = os.path.join(tempfile.gettempdir(), rand, 'testuser', repository.name)
    os.makedirs(working_dir, exist_ok=True)
    r = git.Repo.init(path=working_dir, bare=True)
    assert r.bare is True
    repository.add_remote(remote_name="origin", url=working_dir)

    # Push branches
    # TODO: @billvb - need to refactor this once new branch model is in effect.
    original_branch = repository.git.repo.head.ref.name
    repository.git.repo.heads['master'].checkout()
    repository.git.repo.git.push("origin", "master")

    # Set the head to master on the remote
    r.git.symbolic_ref('HEAD', 'refs/heads/master')

    # Check back out the original user branch
    repository.git.repo.heads[original_branch].checkout()


@pytest.fixture()
def sample_src_file():
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as sample_f:
        # Fill sample file with some deterministic crap
        sample_f.write("n4%nm4%M435A EF87kn*C" * 40)
        sample_f.seek(0)
    yield sample_f.name
    try:
        os.remove(sample_f.name)
    except:
        pass


@pytest.fixture()
def mock_config_file_team():
    """A pytest fixture that creates a temporary directory and a config file to match. Deletes directory after test"""
    conf_file, working_dir = _create_temp_work_dir(override_dict={'core': {'team_mode': True}})
    yield conf_file, working_dir
    shutil.rmtree(working_dir)


@pytest.fixture()
def mock_config_file():
    """A pytest fixture that creates a temporary directory and a config file to match. Deletes directory after test"""
    conf_file, working_dir = _create_temp_work_dir()
    yield conf_file, working_dir
    shutil.rmtree(working_dir)


@pytest.fixture()
def mock_config_file_background_tests():
    """A pytest fixture that creates a temporary directory and a config file to match. Deletes directory after test

    For use primarily with background job tests
    """
    overrides = {"datasets": {
        "cache_manager": "host",
        "hash_cpu_limit": 2,
        "download_cpu_limit": 2,
        "upload_cpu_limit": 2,
        "backends": {
            "gigantum_object_v1": {
                "upload_chunk_size": 4096,
                "download_chunk_size": 4194304,
                "num_workers": 10
                }
            }
        }}
    conf_file, working_dir = _create_temp_work_dir(override_dict=overrides)
    yield conf_file, working_dir
    shutil.rmtree(working_dir)


@pytest.fixture(scope="class")
def mock_config_with_repo():
    """A pytest fixture that creates a temporary directory and a config file to match. Deletes directory after test"""
    conf_file, working_dir = _create_temp_work_dir()
    erm = RepositoryManager(conf_file)
    erm.update_repositories()
    erm.index_repositories()

    yield conf_file, working_dir
    shutil.rmtree(working_dir)


@pytest.fixture(scope="module")
def setup_index():
    """A pytest fixture that creates a temporary directory and a config file to match. Deletes directory after test"""
    # Create a temporary working directory

    conf_file, working_dir = _create_temp_work_dir()

    # Run clone and index operation
    erm = RepositoryManager(conf_file)
    erm.update_repositories()
    erm.index_repositories()

    yield erm, working_dir, conf_file  # provide the fixture value

    # Remove the temp_dir
    shutil.rmtree(working_dir)


@pytest.fixture(scope="module")
def mock_config_file_with_auth():
    """A pytest fixture that creates a temporary directory and a config file to match. Deletes directory after test"""
    # Load auth config for testing
    test_auth_file = os.path.join(resource_filename('gtmcore',
                                                    'auth{}tests'.format(os.path.sep)), 'auth_config.json')
    if not os.path.exists(test_auth_file):
        test_auth_file = f"{test_auth_file}.example"

    with open(test_auth_file, 'rt') as conf:
        auth_data = json.load(conf)

    overrides = {
        'auth': {
            'provider_domain': 'gigantum.auth0.com',
            'signing_algorithm': 'RS256',
            'client_id': auth_data['client_id'],
            'audience': auth_data['audience'],
            'identity_manager': 'local'
        }
    }

    conf_file, working_dir = _create_temp_work_dir(override_dict=overrides)

    # Go get a JWT for the test user from the dev auth client (real users are not in this DB)
    response = requests.post("https://gigantum.auth0.com/oauth/token", json=auth_data)
    token_data = response.json()

    yield conf_file, token_data, working_dir
    shutil.rmtree(working_dir)


@pytest.fixture()
def mock_config_file_with_auth_first_login():
    """A pytest fixture that will run the first login workflow"""
    # Load auth config for testing
    test_auth_file = os.path.join(resource_filename('gtmcore',
                                                    'auth{}tests'.format(os.path.sep)), 'auth_config.json')
    if not os.path.exists(test_auth_file):
        test_auth_file = f"{test_auth_file}.example"

    with open(test_auth_file, 'rt') as conf:
        auth_data = json.load(conf)

    overrides = {
        'auth': {
            'provider_domain': 'gigantum.auth0.com',
            'signing_algorithm': 'RS256',
            'client_id': auth_data['client_id'],
            'audience': auth_data['audience'],
            'identity_manager': 'local'
        },
        'core': {
            'import_demo_on_first_login': True
        }
    }

    # Go get a JWT for the test user from the dev auth client (real users are not in this DB)
    response = requests.post("https://gigantum.auth0.com/oauth/token", json=auth_data)
    token_data = response.json()

    conf_file, working_dir = _create_temp_work_dir(override_dict=overrides)
    yield conf_file, working_dir, token_data  # provide the fixture value
    shutil.rmtree(working_dir)


@pytest.fixture()
def cleanup_auto_import():
    """A pytest fixture that cleans up after the auto-import of the demo"""
    demo_dir = os.path.join('/mnt', 'gigantum', "johndoe", "johndoe", "labbooks", "my-first-project")
    if os.path.exists(demo_dir) is True:
        shutil.rmtree(demo_dir)


@pytest.fixture(scope="module")
def mock_config_file_with_auth_browser():
    """A pytest fixture that creates a temporary directory and a config file to match. Deletes directory after test"""
    # Load auth config for testing
    test_auth_file = os.path.join(resource_filename('gtmcore',
                                                    'auth{}tests'.format(os.path.sep)), 'auth_config.json')
    if not os.path.exists(test_auth_file):
        test_auth_file = f"{test_auth_file}.example"

    with open(test_auth_file, 'rt') as conf:
        auth_data = json.load(conf)

    overrides = {
        'auth': {
            'provider_domain': 'gigantum.auth0.com',
            'signing_algorithm': 'RS256',
            'client_id': auth_data['client_id'],
            'audience': auth_data['audience'],
            'identity_manager': 'browser'
        }
    }

    conf_file, working_dir = _create_temp_work_dir(override_dict=overrides)

    # Go get a JWT for the test user from the dev auth client (real users are not in this DB)
    response = requests.post("https://gigantum.auth0.com/oauth/token", json=auth_data)
    token_data = response.json()

    yield conf_file, working_dir, token_data
    shutil.rmtree(working_dir)


@pytest.fixture()
def mock_config_with_activitystore():
    """A pytest fixture that creates a ActivityStore (and labbook) and deletes directory after test"""
    # Create a temporary working directory
    conf_file, working_dir = _create_temp_work_dir()
    im = InventoryManager(conf_file)
    lb = im.create_labbook('default', 'default', 'labbook1', description="my first labbook",
                           author=GitAuthor("default", "default@test.com"))
    store = ActivityStore(lb)

    yield store, lb

    # Remove the temp_dir
    shutil.rmtree(working_dir)


@pytest.fixture()
def mock_config_with_detaildb():
    """A pytest fixture that creates a detail db (and labbook) and deletes directory after test"""
    # Create a temporary working directory
    conf_file, working_dir = _create_temp_work_dir()
    im = InventoryManager(conf_file)
    lb = im.create_labbook('default', 'default', 'labbook1', description="my first labbook")
    db = ActivityDetailDB(lb.root_dir, lb.checkout_id)

    yield db, lb

    # Remove the temp_dir
    shutil.rmtree(working_dir)


@pytest.fixture()
def mock_labbook():
    """A pytest fixture that creates a temporary directory and a config file to match.
    Deletes directory after test"""

    conf_file, working_dir = _create_temp_work_dir()
    erm = RepositoryManager(conf_file)
    erm.update_repositories()
    erm.index_repositories()

    im = InventoryManager(conf_file)
    # description was "my first labbook1"
    lb = im.create_labbook('test', 'test', 'labbook1', description="my test description")
    yield conf_file, lb.root_dir, lb
    shutil.rmtree(working_dir)


@pytest.fixture()
def mock_labbook_lfs_disabled():
    """A pytest fixture that creates a temporary directory and a config file to match. Deletes directory after test"""

    conf_file, working_dir = _create_temp_work_dir(lfs_enabled=False)
    im = InventoryManager(conf_file)
    lb = im.create_labbook_disabled_lfs('test', 'test', 'labbook1', description="my first labbook")
    assert lb.is_repo_clean
    yield conf_file, lb.root_dir, lb
    shutil.rmtree(working_dir)


@pytest.fixture()
def mock_config_lfs_disabled():
    conf_file, working_dir = _create_temp_work_dir(lfs_enabled=False)
    yield conf_file, working_dir


@pytest.fixture()
def mock_duplicate_labbook():
    """A pytest fixture that creates a temporary directory and a config file to match. Deletes directory after test"""

    conf_file, working_dir = _create_temp_work_dir()
    im = InventoryManager(conf_file)
    lb = im.create_labbook('test', 'test', 'labbook1', description="my first labbook")
    yield conf_file, lb.root_dir, lb
    shutil.rmtree(working_dir)


@pytest.fixture()
def remote_labbook_repo():

    # TODO: Remove after integration tests with LFS support are available
    conf_file, working_dir = _create_temp_work_dir(lfs_enabled=False)
    im = InventoryManager(conf_file)
    lb = im.create_labbook('test', 'test', 'sample-repo-lb', description="my first labbook")
    bm = BranchManager(lb, username='test')
    bm.create_branch('testing-branch')


    #with tempfile.TemporaryDirectory() as tmpdirname:
    with open(os.path.join('/tmp', 'codefile.c'), 'wb') as codef:
        codef.write(b'// Cody McCodeface ...')

    FileOperations.insert_file(lb, "code", "/tmp/codefile.c")

    assert lb.is_repo_clean
    bm.workon_branch('master')

    # Location of the repo to push/pull from
    yield lb.root_dir
    shutil.rmtree(working_dir)
    try:
        os.remove('/tmp/codefile.c')
    except:
        pass


@pytest.fixture()
def remote_bare_repo():
    conf_file, working_dir = _create_temp_work_dir()
    import git
    r = git.Repo.init(path=working_dir, bare=True)
    assert r.bare is True

    yield working_dir
    shutil.rmtree(working_dir)


@pytest.fixture()
def labbook_dir_tree():
    with tempfile.TemporaryDirectory() as tempdir:

        subdirs = [['.gigantum'],
                   ['.gigantum', 'env'],
                   ['.gigantum', 'env', 'base'],
                   ['.gigantum', 'env', 'custom'],
                   ['.gigantum', 'env', 'package_manager']]

        for subdir in subdirs:
            os.makedirs(os.path.join(tempdir, "my-temp-labbook", *subdir), exist_ok=True)

        with tempfile.TemporaryDirectory() as checkoutdir:
            repo = git.Repo.clone_from("https://github.com/gigantum/base-images-testing.git", checkoutdir)
            shutil.copy(os.path.join(checkoutdir, "base/quickstart-jupyterlab/quickstart-jupyterlab_r0.yaml"),
                        os.path.join(tempdir, "my-temp-labbook", ".gigantum", "env", "base"))
            shutil.copy(os.path.join(checkoutdir, "custom/pillow/pillow_r0.yaml"),
                        os.path.join(tempdir, "my-temp-labbook", ".gigantum", "env", "custom"))

        yield os.path.join(tempdir, 'my-temp-labbook')


@pytest.fixture()
def get_jwt():
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as sample_f:
        # Fill sample file with some deterministic crap
        sample_f.write("n4%nm4%M435A EF87kn*C" * 40)
        sample_f.seek(0)
    yield sample_f.name
    try:
        os.remove(sample_f.name)
    except:
        pass
