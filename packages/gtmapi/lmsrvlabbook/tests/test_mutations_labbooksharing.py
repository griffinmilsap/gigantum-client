import os
import io
import math
import tempfile
import responses
from graphene.test import Client
from mock import patch
from werkzeug.datastructures import FileStorage
from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Request


from gtmcore.dispatcher.jobs import export_labbook_as_zip

from lmsrvcore.middleware import DataloaderMiddleware
from lmsrvlabbook.tests.fixtures import (property_mocks_fixture, docker_socket_fixture,
    fixture_working_dir, fixture_working_dir_lfs_disabled)

import pytest
from mock import patch
from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Request

from gtmcore.fixtures import remote_labbook_repo, mock_config_file, _MOCK_create_remote_repo2
from gtmcore.workflows import LabbookWorkflow, GitWorkflow
from gtmcore.inventory.inventory import InventoryManager
from gtmcore.configuration import Configuration
from gtmcore.dispatcher import Dispatcher, JobKey
from gtmcore.files import FileOperations

@pytest.fixture()
def mock_create_labbooks(fixture_working_dir):
    # Create a labbook in the temporary directory
    lb = InventoryManager(fixture_working_dir[0]).create_labbook("default", "default", "sample-repo-lb",
                                                                 description="Cats labbook 1")

    # Create a file in the dir
    with open(os.path.join(fixture_working_dir[1], 'codefile.c'), 'w') as sf:
        sf.write("1234567")
        sf.seek(0)
    FileOperations.insert_file(lb, 'code', sf.name)

    assert os.path.isfile(os.path.join(lb.root_dir, 'code', 'codefile.c'))
    # name of the config file, temporary working directory, the schema
    yield fixture_working_dir, lb


@pytest.fixture()
def mock_create_labbooks_2(fixture_working_dir):
    # Create a labbook in the temporary directory
    im = InventoryManager(fixture_working_dir[0])
    lb = im.create_labbook("default", "default", "labbook1", "Test labbook 1")

    yield fixture_working_dir


@pytest.fixture()
def mock_create_labbooks_no_lfs(fixture_working_dir_lfs_disabled):
    # Create a labbook in the temporary directory
    im = InventoryManager(fixture_working_dir_lfs_disabled[0])
    lb = im.create_labbook("default", "default", "labbook1",
                           description="Cats labbook 1")

    # Create a file in the dir
    with open(os.path.join(fixture_working_dir_lfs_disabled[1], 'sillyfile'), 'w') as sf:
        sf.write("1234567")
        sf.seek(0)
    FileOperations.insert_file(lb, 'code', sf.name)

    assert os.path.isfile(os.path.join(lb.root_dir, 'code', 'sillyfile'))
    # name of the config file, temporary working directory, the schema
    yield fixture_working_dir_lfs_disabled


class TestMutationsLabbookSharing(object):

    @responses.activate
    def test_import_remote_labbook(self, remote_labbook_repo, fixture_working_dir, property_mocks_fixture,
                                   docker_socket_fixture, monkeypatch):

        # Mock the request context so a fake authorization header is present
        builder = EnvironBuilder(path='/labbook', method='POST', headers={'Authorization': 'Bearer AJDFHASD'})
        env = builder.get_environ()
        req = Request(environ=env)

        monkeypatch.setattr(Configuration, 'find_default_config', lambda x : fixture_working_dir[0])

        def mock_dispatch(*args, **kwargs):
            return JobKey('rq:job:000-000-000')
        monkeypatch.setattr(Dispatcher, 'dispatch_task', mock_dispatch)

        query = f"""
        mutation importFromRemote {{
          importRemoteLabbook(
            input: {{
              owner: "test",
              labbookName: "sample-repo-lb",
              remoteUrl: "{remote_labbook_repo}"
            }}) {{
                jobKey
            }}
        }}
        """
        r = fixture_working_dir[2].execute(query, context_value=req)
        assert 'errors' not in r
        assert r['data']['importRemoteLabbook']['jobKey'] == 'rq:job:000-000-000'

    def test_can_checkout_branch(self, mock_create_labbooks, remote_labbook_repo, fixture_working_dir):
        """Test whether there are uncommitted changes or anything that would prevent
        having a fresh branch checked out. """

        f_dir, lb = mock_create_labbooks

        query = f"""
        {{
            labbook(name: "sample-repo-lb", owner: "default") {{
                isRepoClean
            }}
        }}
        """
        r = fixture_working_dir[2].execute(query)
        assert r['data']['labbook']['isRepoClean'] is True

        os.remove(os.path.join(lb.root_dir, 'code', 'codefile.c'))

        r = fixture_working_dir[2].execute(query)
        # We back-door deleted a file in the LB. The repo should now be unclean - prove it.
        assert r['data']['labbook']['isRepoClean'] is False

    def test_delete_remote_labbook_dryrun(self, fixture_working_dir):
        """Test deleting a LabBook on a remote server - dry run"""

        delete_query = f"""
        mutation delete {{
            deleteRemoteLabbook(input: {{
                owner: "default",
                labbookName: "new-labbook",
                confirm: false
            }}) {{
                success
            }}
        }}
        """
        r = fixture_working_dir[2].execute(delete_query)
        print(r)
        assert 'errors' not in r
        assert r['data']['deleteRemoteLabbook']['success'] is False

    @responses.activate
    def test_delete_remote_labbook(self, fixture_working_dir):
        """Test deleting a LabBook on a remote server"""
        # Setup responses mock for this test
        responses.add(responses.GET, 'https://usersrv.gigantum.io/key',
                      json={'key': 'afaketoken'}, status=200)
        responses.add(responses.GET, 'https://repo.gigantum.io/api/v4/projects/default%2Fnew-labbook',
                      json=[{
                              "id": 27,
                              "description": "",
                            }],
                      status=200)
        responses.add(responses.DELETE, 'https://repo.gigantum.io/api/v4/projects/default%2Fnew-labbook',
                      json={
                                "message": "202 Accepted"
                            },
                      status=202)
        responses.add(responses.GET, 'https://repo.gigantum.io/api/v4/projects/default%2Fnew-labbook',
                      json=[{
                                "message": "404 Project Not Found"
                            }],
                      status=404)
        responses.add(responses.DELETE, 'https://api.gigantum.com/read/index/default%2Fnew-labbook',
                      json=[{
                                "message": "success"
                            }],
                      status=204)


        im = InventoryManager(fixture_working_dir[0])
        lb = im.create_labbook("default", "default", "new-labbook")

        delete_query = f"""
        mutation delete {{
            deleteRemoteLabbook(input: {{
                owner: "default",
                labbookName: "new-labbook",
                confirm: true
            }}) {{
                success
            }}
        }}
        """

        r = fixture_working_dir[2].execute(delete_query)
        assert 'errors' not in r
        assert r['data']['deleteRemoteLabbook']['success'] is True

        # Try deleting again, which should return an error
        r2 = fixture_working_dir[2].execute(delete_query)
        assert 'errors' in r2

    @patch('gtmcore.workflows.gitworkflows_utils.create_remote_gitlab_repo', new=_MOCK_create_remote_repo2)
    def test_publish_basic(self, fixture_working_dir, mock_create_labbooks_no_lfs):

        # Mock the request context so a fake authorization header is present
        builder = EnvironBuilder(path='/labbook', method='POST', headers={'Authorization': 'Bearer AJDFHASD'})
        env = builder.get_environ()
        req = Request(environ=env)

        im = InventoryManager(mock_create_labbooks_no_lfs[0])
        test_user_lb = im.load_labbook('default', 'default', 'labbook1')

        publish_query = f"""
        mutation c {{
            publishLabbook(input: {{
                labbookName: "labbook1",
                owner: "default"
            }}) {{
                jobKey
            }}
        }}
        """

        r = mock_create_labbooks_no_lfs[2].execute(publish_query, context_value=req)
        assert 'errors' not in r
        # TODO - Pause and wait for bg job to finish
        #assert r['data']['publishLabbook']['success'] is True

    @responses.activate
    @patch('gtmcore.workflows.gitworkflows_utils.create_remote_gitlab_repo', new=_MOCK_create_remote_repo2)
    def test_sync_1(self, mock_create_labbooks_no_lfs, mock_config_file):

        # Setup responses mock for this test
        responses.add(responses.GET, 'https://usersrv.gigantum.io/key',
                      json={'key': 'afaketoken'}, status=200)

        im = InventoryManager(mock_create_labbooks_no_lfs[0])
        test_user_lb = im.load_labbook('default', 'default', 'labbook1')
        test_user_wf = LabbookWorkflow(test_user_lb)
        test_user_wf.publish('default')

        # Mock the request context so a fake authorization header is present
        builder = EnvironBuilder(path='/labbook', method='POST', headers={'Authorization': 'Bearer AJDFHASD'})
        env = builder.get_environ()
        req = Request(environ=env)


        sally_wf = LabbookWorkflow.import_from_remote(test_user_wf.remote, 'sally', config_file=mock_config_file[0])
        sally_lb = sally_wf.labbook
        FileOperations.makedir(sally_lb, relative_path='code/sally-dir', create_activity_record=True)
        sally_wf.sync('sally')

        sync_query = """
        mutation x {
            syncLabbook(input: {
                labbookName: "labbook1",
                owner: "default"
            }) {
                jobKey
            }
        }
        """
        r = mock_create_labbooks_no_lfs[2].execute(sync_query, context_value=req)

        assert 'errors' not in r
        # TODO - Pause and wait for job to report finished

    @patch('gtmcore.workflows.gitworkflows_utils.create_remote_gitlab_repo', new=_MOCK_create_remote_repo2)
    def test_reset_branch_to_remote(self, fixture_working_dir, mock_create_labbooks_no_lfs):
        # Mock the request context so a fake authorization header is present
        builder = EnvironBuilder(path='/labbook', method='POST', headers={'Authorization': 'Bearer AJDFHASD'})
        env = builder.get_environ()
        req = Request(environ=env)

        im = InventoryManager(mock_create_labbooks_no_lfs[0])
        test_user_lb = im.load_labbook('default', 'default', 'labbook1')
        wf = LabbookWorkflow(test_user_lb)
        wf.publish(username='default')
        hash_original = wf.labbook.git.commit_hash

        new_file_path = os.path.join(wf.labbook.root_dir, 'input', 'new-file')
        with open(new_file_path, 'w') as f: f.write('File data')
        wf.labbook.sweep_uncommitted_changes()
        hash_before_reset = wf.labbook.git.commit_hash

        publish_query = f"""
        mutation c {{
            resetBranchToRemote(input: {{
                labbookName: "labbook1",
                owner: "default"
            }}) {{
                labbook {{
                    activeBranchName
                }}
            }}
        }}
        """

        r = mock_create_labbooks_no_lfs[2].execute(publish_query, context_value=req)
        assert 'errors' not in r
        assert wf.labbook.git.commit_hash == hash_original
        # hash_after_reset = r['data']['resetBranchToRemote']['labbook']['activeBranch']['commit']['shortHash']
        # assert hash_after_reset not in hash_before_reset
        # assert hash_after_reset in hash_original

    def test_import_labbook(self, fixture_working_dir):
        """Test batch uploading, but not full import"""
        class DummyContext(object):
            def __init__(self, file_handle):
                self.labbook_loader = None
                self.files = {'uploadChunk': file_handle}

        client = Client(fixture_working_dir[3], middleware=[DataloaderMiddleware()])

        # Create a temporary labbook
        lb = InventoryManager(fixture_working_dir[0]).create_labbook("default", "default", "test-export",
                                                                     description="Tester")

        # Create a largeish file in the dir
        with open(os.path.join(fixture_working_dir[1], 'testfile.bin'), 'wb') as testfile:
            testfile.write(os.urandom(9000000))
        FileOperations.insert_file(lb, 'input', testfile.name)

        # Export labbook
        zip_file = export_labbook_as_zip(lb.root_dir, tempfile.gettempdir())
        lb_dir = lb.root_dir

        # Get upload params
        chunk_size = 4194304
        file_info = os.stat(zip_file)
        file_size = int(file_info.st_size / 1000)
        total_chunks = int(math.ceil(file_info.st_size/chunk_size))

        with open(zip_file, 'rb') as tf:
            for chunk_index in range(total_chunks):
                chunk = io.BytesIO()
                chunk.write(tf.read(chunk_size))
                chunk.seek(0)
                file = FileStorage(chunk)

                query = f"""
                            mutation myMutation{{
                              importLabbook(input:{{
                                chunkUploadParams:{{
                                  uploadId: "jfdjfdjdisdjwdoijwlkfjd",
                                  chunkSize: {chunk_size},
                                  totalChunks: {total_chunks},
                                  chunkIndex: {chunk_index},
                                  fileSize: "{file_size}",
                                  filename: "{os.path.basename(zip_file)}"
                                }}
                              }}) {{
                                importJobKey
                              }}
                            }}
                            """
                result = client.execute(query, context_value=DummyContext(file))
                assert "errors" not in result
                if chunk_index == total_chunks - 1:
                    assert type(result['data']['importLabbook']['importJobKey']) == str
                    assert "rq:job:" in result['data']['importLabbook']['importJobKey']

                chunk.close()

    @responses.activate
    def test_add_collaborator(self, mock_create_labbooks_2, property_mocks_fixture):
        """Test adding a collaborator to a LabBook"""
        # Setup REST mocks
        responses.add(responses.GET, 'https://repo.gigantum.io/api/v4/users?username=person100',
                      json=[
                                {
                                    "id": 100,
                                    "name": "New Person",
                                    "username": "person100",
                                    "state": "active",
                                    "access_level": 30
                                }
                            ],
                      status=200)
        responses.add(responses.GET, 'https://repo.gigantum.io/api/v4/projects/default%2Flabbook1/members',
                      json=[
                                {
                                    "id": 29,
                                    "name": "Jane Doe",
                                    "username": "default",
                                    "access_level": 40,
                                    "expires_at": None
                                }
                            ],
                      status=200)
        responses.add(responses.POST, 'https://repo.gigantum.io/api/v4/projects/default%2Flabbook1/members',
                      json={
                                "id": 100,
                                "name": "New Person",
                                "username": "person100",
                                "state": "active",
                            },
                      status=201)
        responses.add(responses.GET, 'https://repo.gigantum.io/api/v4/projects/default%2Flabbook1',
                      json=[{
                              "id": 27,
                              "description": "",
                            }],
                      status=200)
        responses.add(responses.GET, 'https://repo.gigantum.io/api/v4/projects/default%2Flabbook1/members',
                      json=[
                                {
                                    "id": 29,
                                    "name": "Jane Doe",
                                    "username": "default",
                                    "access_level": 40,
                                    "expires_at": None
                                },
                                {
                                    "id": 100,
                                    "name": "New Person",
                                    "username": "person100",
                                    "access_level": 30,
                                    "expires_at": None
                                }
                            ],
                      status=200)

        # Mock the request context so a fake authorization header is present
        builder = EnvironBuilder(path='/labbook', method='POST', headers={'Authorization': 'Bearer AJDFHASD'})
        env = builder.get_environ()
        req = Request(environ=env)

        query = """
        mutation AddCollaborator {
          addCollaborator(
            input: {
              owner: "default",
              labbookName: "labbook1",
              username: "person100"
              permissions: "readwrite"
            }) {
              updatedLabbook {
                collaborators {
                    collaboratorUsername
                    permission
                }
                canManageCollaborators
              }
            }
        }
        """
        r = mock_create_labbooks_2[2].execute(query, context_value=req)
        assert 'errors' not in r
        assert r['data']['addCollaborator']['updatedLabbook']['collaborators'][0]['collaboratorUsername'] == 'default'
        assert r['data']['addCollaborator']['updatedLabbook']['collaborators'][0]['permission'] == 'OWNER'
        assert r['data']['addCollaborator']['updatedLabbook']['collaborators'][1]['collaboratorUsername'] == 'person100'
        assert r['data']['addCollaborator']['updatedLabbook']['collaborators'][1]['permission'] == 'READ_WRITE'
        assert r['data']['addCollaborator']['updatedLabbook']['canManageCollaborators'] is True

    @responses.activate
    def test_add_collaborator_as_owner(self, mock_create_labbooks_2, property_mocks_fixture):
        """Test adding a collaborator to a LabBook"""
        # Setup REST mocks
        responses.add(responses.GET, 'https://repo.gigantum.io/api/v4/users?username=person100',
                      json=[
                                {
                                    "id": 100,
                                    "name": "New Person",
                                    "username": "person100",
                                    "state": "active",
                                    "access_level": 30
                                }
                            ],
                      status=200)
        responses.add(responses.GET, 'https://repo.gigantum.io/api/v4/projects/default%2Flabbook1/members',
                      json=[
                                {
                                    "id": 29,
                                    "name": "Jane Doe",
                                    "username": "default",
                                    "access_level": 40,
                                    "expires_at": None
                                }
                            ],
                      status=200)
        responses.add(responses.POST, 'https://repo.gigantum.io/api/v4/projects/default%2Flabbook1/members',
                      json={
                                "id": 100,
                                "name": "New Person",
                                "username": "person100",
                                "state": "active",
                            },
                      status=201)
        responses.add(responses.GET, 'https://repo.gigantum.io/api/v4/projects/default%2Flabbook1',
                      json=[{
                              "id": 27,
                              "description": "",
                            }],
                      status=200)
        responses.add(responses.GET, 'https://repo.gigantum.io/api/v4/projects/default%2Flabbook1/members',
                      json=[
                                {
                                    "id": 29,
                                    "name": "Jane Doe",
                                    "username": "default",
                                    "access_level": 40,
                                    "expires_at": None
                                },
                                {
                                    "id": 100,
                                    "name": "New Person",
                                    "username": "person100",
                                    "access_level": 40,
                                    "expires_at": None
                                }
                            ],
                      status=200)
        # Mock the request context so a fake authorization header is present
        builder = EnvironBuilder(path='/labbook', method='POST', headers={'Authorization': 'Bearer AJDFHASD'})
        env = builder.get_environ()
        req = Request(environ=env)

        query = """
        mutation AddCollaborator {
          addCollaborator(
            input: {
              owner: "default",
              labbookName: "labbook1",
              username: "person100"
              permissions: "owner"
            }) {
              updatedLabbook {
                collaborators {
                    collaboratorUsername
                    permission
                }
                canManageCollaborators
              }
            }
        }
        """
        r = mock_create_labbooks_2[2].execute(query, context_value=req)
        assert 'errors' not in r
        assert r['data']['addCollaborator']['updatedLabbook']['collaborators'][0]['collaboratorUsername'] == 'default'
        assert r['data']['addCollaborator']['updatedLabbook']['collaborators'][0]['permission'] == 'OWNER'
        assert r['data']['addCollaborator']['updatedLabbook']['collaborators'][1]['collaboratorUsername'] == 'person100'
        assert r['data']['addCollaborator']['updatedLabbook']['collaborators'][1]['permission'] == 'OWNER'

    @responses.activate
    def test_delete_collaborator(self, mock_create_labbooks_2, property_mocks_fixture):
        """Test deleting a collaborator from a LabBook"""
        # Setup REST mocks
        responses.add(responses.GET, 'https://repo.gigantum.io/api/v4/users?username=person100',
                      json=[
                                {
                                    "id": 100,
                                    "name": "New Person",
                                    "username": "person100",
                                    "state": "active",
                                }
                            ],
                      status=200)
        responses.add(responses.DELETE, 'https://repo.gigantum.io/api/v4/projects/default%2Flabbook1/members/100',
                      status=204)
        responses.add(responses.GET, 'https://repo.gigantum.io/api/v4/projects/default%2Flabbook1',
                      json=[{
                              "id": 27,
                              "description": "",
                            }],
                      status=200)
        responses.add(responses.GET, 'https://repo.gigantum.io/api/v4/projects/default%2Flabbook1/members',
                      json=[
                                {
                                    "id": 29,
                                    "name": "Jane Doe",
                                    "username": "default",
                                    "access_level": 40,
                                    "expires_at": None
                                }
                            ],
                      status=200)

        # Mock the request context so a fake authorization header is present
        builder = EnvironBuilder(path='/labbook', method='DELETE', headers={'Authorization': 'Bearer AJDFHASD'})
        env = builder.get_environ()
        req = Request(environ=env)

        query = """
        mutation DeleteCollaborator {
          deleteCollaborator(
            input: {
              owner: "default",
              labbookName: "labbook1",
              username: "person100"
            }) {
              updatedLabbook {
                collaborators {
                    collaboratorUsername
                }
              }
            }
        }
        """
        r = mock_create_labbooks_2[2].execute(query, context_value=req)
        assert 'errors' not in r
        assert r['data']['deleteCollaborator']['updatedLabbook']['collaborators'][0]['collaboratorUsername'] == 'default'

    @responses.activate
    def test_change_collaborator_permissions(self, mock_create_labbooks_2, property_mocks_fixture):
        """Test changing the permissions of a collaborator"""
        # Setup REST mocks
        responses.add(responses.GET, 'https://repo.gigantum.io/api/v4/users?username=person100',
                      json=[
                                {
                                    "id": 100,
                                    "name": "New Person",
                                    "username": "person100",
                                    "state": "active",
                                    "access_level": 30
                                }
                            ],
                      status=200)
        responses.add(responses.GET, 'https://repo.gigantum.io/api/v4/projects/default%2Flabbook1/members',
                      json=[
                                {
                                    "id": 29,
                                    "name": "Jane Doe",
                                    "username": "default",
                                    "access_level": 40,
                                    "expires_at": None
                                },
                                {
                                    "id": 100,
                                    "name": "New Person",
                                    "username": "person100",
                                    "access_level": 30,
                                    "expires_at": None
                                }
                            ],
                      status=200)
        responses.add(responses.POST, 'https://repo.gigantum.io/api/v4/projects/default%2Flabbook1/members',
                      json={
                                "id": 100,
                                "name": "New Person",
                                "username": "person100",
                                "state": "active",
                            },
                      status=201)
        responses.add(responses.GET, 'https://repo.gigantum.io/api/v4/projects/default%2Flabbook1',
                      json=[{
                              "id": 27,
                              "description": "",
                            }],
                      status=200)
        responses.add(responses.DELETE, 'https://repo.gigantum.io/api/v4/projects/default%2Flabbook1/members/100',
                      status=204)
        responses.add(responses.GET, 'https://repo.gigantum.io/api/v4/projects/default%2Flabbook1/members',
                      json=[
                                {
                                    "id": 29,
                                    "name": "Jane Doe",
                                    "username": "default",
                                    "access_level": 40,
                                    "expires_at": None
                                },
                                {
                                    "id": 100,
                                    "name": "New Person",
                                    "username": "person100",
                                    "access_level": 20,
                                    "expires_at": None
                                }
                            ],
                      status=200)

        # Mock the request context so a fake authorization header is present
        builder = EnvironBuilder(path='/labbook', method='POST', headers={'Authorization': 'Bearer AJDFHASD'})
        env = builder.get_environ()
        req = Request(environ=env)

        query = """
        mutation AddCollaborator {
          addCollaborator(
            input: {
              owner: "default",
              labbookName: "labbook1",
              username: "person100"
              permissions: "readonly"
            }) {
              updatedLabbook {
                collaborators {
                    collaboratorUsername
                    permission
                }
                canManageCollaborators
              }
            }
        }
        """
        r = mock_create_labbooks_2[2].execute(query, context_value=req)
        assert 'errors' not in r
        assert r['data']['addCollaborator']['updatedLabbook']['collaborators'][0]['collaboratorUsername'] == 'default'
        assert r['data']['addCollaborator']['updatedLabbook']['collaborators'][0]['permission'] == 'OWNER'
        assert r['data']['addCollaborator']['updatedLabbook']['collaborators'][1]['collaboratorUsername'] == 'person100'
        assert r['data']['addCollaborator']['updatedLabbook']['collaborators'][1]['permission'] == 'READ_ONLY'
        assert r['data']['addCollaborator']['updatedLabbook']['canManageCollaborators'] is True

    @responses.activate
    def test_not_owner_permissions(self, mock_create_labbooks_2, property_mocks_fixture):
        """Test changing the permissions of a collaborator"""
        # Setup REST mocks
        responses.add(responses.GET, 'https://repo.gigantum.io/api/v4/projects/default%2Flabbook1',
                      json=[{
                              "id": 27,
                              "description": "",
                            }],
                      status=200)
        responses.add(responses.GET, 'https://repo.gigantum.io/api/v4/projects/default%2Flabbook1/members',
                      json=[
                                {
                                    "id": 29,
                                    "name": "Jane Doe",
                                    "username": "default",
                                    "access_level": 40,
                                    "expires_at": None
                                }
                            ],
                      status=200)
        responses.add(responses.GET, 'https://repo.gigantum.io/api/v4/projects/default%2Flabbook1/members',
                      json=[
                                {
                                    "id": 29,
                                    "name": "Jane Doe",
                                    "username": "default",
                                    "access_level": 30,
                                    "expires_at": None
                                }
                            ],
                      status=200)
        responses.add(responses.GET, 'https://repo.gigantum.io/api/v4/projects/default%2Flabbook1/members',
                      json=[
                                {
                                    "id": 29,
                                    "name": "Jane Doe",
                                    "username": "default",
                                    "access_level": 20,
                                    "expires_at": None
                                }
                            ],
                      status=200)

        # Mock the request context so a fake authorization header is present
        builder = EnvironBuilder(path='/labbook', method='GET', headers={'Authorization': 'Bearer AJDFHASD'})
        env = builder.get_environ()
        req = Request(environ=env)

        query = """{
              labbook(owner: "default", name: "labbook1") {
                canManageCollaborators
              }
        }
        """
        # Mock getting back OWNER perms
        r = mock_create_labbooks_2[2].execute(query, context_value=req)
        assert 'errors' not in r
        assert r['data']['labbook']['canManageCollaborators'] is True

        # Mock getting back READ_WRITE perms
        r = mock_create_labbooks_2[2].execute(query, context_value=req)
        assert 'errors' not in r
        assert r['data']['labbook']['canManageCollaborators'] is False

        # Mock getting back READ_ONLY
        r = mock_create_labbooks_2[2].execute(query, context_value=req)
        assert 'errors' not in r
        assert r['data']['labbook']['canManageCollaborators'] is False
