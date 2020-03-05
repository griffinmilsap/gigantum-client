import pytest
import os
import uuid
import flask
from mock import patch

from snapshottest import snapshot
from lmsrvlabbook.tests.fixtures import fixture_working_dir_env_repo_scoped, fixture_working_dir

from gtmcore.inventory.inventory import InventoryManager
from gtmcore.dataset.io.manager import IOManager
from gtmcore.dataset.manifest import Manifest
from gtmcore.dispatcher import Dispatcher

from gtmcore.fixtures.datasets import mock_dataset_with_cache_dir, mock_dataset_with_manifest, helper_append_file, \
    helper_compress_file


class JobResponseMock(object):
    def __init__(self, key):
        self.key_str = key


class TestDatasetFilesMutations(object):
    def test_download_dataset_files(self, fixture_working_dir, snapshot):
        def dispatcher_mock(self, function_ref, kwargs, metadata, persist):
            assert kwargs['logged_in_username'] == 'default'
            assert kwargs['access_token'] == 'asdf'
            assert kwargs['id_token'] == '1234'
            assert kwargs['dataset_owner'] == 'default'
            assert kwargs['dataset_name'] == 'dataset100'
            assert kwargs['labbook_owner'] is None
            assert kwargs['labbook_name'] is None
            assert kwargs['all_keys'] is None
            assert kwargs['keys'] == ["test1.txt"]
            assert persist is True

            assert metadata['dataset'] == 'default|default|dataset100'
            assert metadata['labbook'] is None
            assert metadata['method'] == 'download_dataset_files'

            return JobResponseMock("rq:job:00923477-d46b-479c-ad0c-2b66f90b6b10")

        im = InventoryManager(fixture_working_dir[0])
        ds = im.create_dataset('default', 'default', "dataset100", storage_type="gigantum_object_v1", description="100")

        flask.g.access_token = "asdf"
        flask.g.id_token = "1234"

        with patch.object(Dispatcher, 'dispatch_task', dispatcher_mock):

            query = """
                       mutation myMutation {
                         downloadDatasetFiles(input: {datasetOwner: "default", datasetName: "dataset100", keys: ["test1.txt"]}) {
                             backgroundJobKey 
                         }
                       }
                       """
            r = fixture_working_dir[2].execute(query)
            assert 'errors' not in r
            assert isinstance(r['data']['downloadDatasetFiles']['backgroundJobKey'], str)
            assert "rq:" in r['data']['downloadDatasetFiles']['backgroundJobKey']

    def test_download_dataset_files_linked(self, fixture_working_dir, snapshot):

        def dispatcher_mock(self, function_ref, kwargs, metadata, persist):
            assert kwargs['logged_in_username'] == 'default'
            assert kwargs['access_token'] == 'asdf'
            assert kwargs['id_token'] == '1234'
            assert kwargs['dataset_owner'] == 'default'
            assert kwargs['dataset_name'] == 'dataset100'
            assert kwargs['labbook_owner'] == 'default'
            assert kwargs['labbook_name'] == 'test-lb'
            assert kwargs['all_keys'] is None
            assert kwargs['keys'] == ["test1.txt"]
            assert persist is True

            assert metadata['dataset'] == 'default|default|test-lb|LINKED|default|default|dataset100'
            assert metadata['labbook'] == 'default|default|test-lb'
            assert metadata['method'] == 'download_dataset_files'

            return JobResponseMock("rq:job:00923477-d46b-479c-ad0c-2b66f90b6b10")

        im = InventoryManager(fixture_working_dir[0])
        ds = im.create_dataset('default', 'default', "dataset100", storage_type="gigantum_object_v1", description="100")
        lb = im.create_labbook('default', 'default', "test-lb", description="tester")
        im.link_dataset_to_labbook(f"{ds.root_dir}/.git", 'default', 'dataset100', lb, 'default')

        flask.g.access_token = "asdf"
        flask.g.id_token = "1234"

        with patch.object(Dispatcher, 'dispatch_task', dispatcher_mock):

            query = """
                       mutation myMutation {
                         downloadDatasetFiles(input: {datasetOwner: "default", datasetName: "dataset100", keys: ["test1.txt"], labbookOwner: "default", labbookName: "test-lb"}){
                             backgroundJobKey 
                         }
                       }
                       """
            r = fixture_working_dir[2].execute(query)
            assert 'errors' not in r
            assert isinstance(r['data']['downloadDatasetFiles']['backgroundJobKey'], str)
            assert "rq:" in r['data']['downloadDatasetFiles']['backgroundJobKey']

    def test_delete_dataset_files(self, fixture_working_dir, snapshot):
        im = InventoryManager(fixture_working_dir[0])
        ds = im.create_dataset('default', 'default', "dataset-delete",
                               storage_type="gigantum_object_v1", description="testing delete")
        m = Manifest(ds, 'default')

        os.makedirs(os.path.join(m.cache_mgr.cache_root, m.dataset_revision, "other_dir"))
        helper_append_file(m.cache_mgr.cache_root, m.dataset_revision, "test1.txt", "asdfadfsdf")
        helper_append_file(m.cache_mgr.cache_root, m.dataset_revision, "test2.txt", "fdsfgfd")
        helper_append_file(m.cache_mgr.cache_root, m.dataset_revision, "test3.txt", "ghgdsr")
        helper_append_file(m.cache_mgr.cache_root, m.dataset_revision, "other_dir/test3.txt", "hhgf")
        helper_append_file(m.cache_mgr.cache_root, m.dataset_revision, "other_dir/test1.txt", "jkjghfg")
        m.sweep_all_changes()

        revision = m.dataset_revision
        assert os.path.exists(os.path.join(m.cache_mgr.cache_root, revision, "test1.txt")) is True
        assert os.path.exists(os.path.join(m.cache_mgr.cache_root, revision, "test2.txt")) is True
        assert os.path.exists(os.path.join(m.cache_mgr.cache_root, revision, "test3.txt")) is True
        assert os.path.exists(os.path.join(m.cache_mgr.cache_root, revision, "other_dir", "test3.txt")) is True
        assert os.path.exists(os.path.join(m.cache_mgr.cache_root, revision, "other_dir", "test1.txt")) is True

        query = """
                   mutation myMutation {
                     deleteDatasetFiles(input: {datasetOwner: "default", datasetName: "dataset-delete", 
                                                keys: ["test1.txt"]}) {
                         success
                     }
                   }
                   """
        result = fixture_working_dir[2].execute(query)
        assert 'errors' not in result
        assert result['data']['deleteDatasetFiles']['success'] is True

        revision = m.dataset_revision
        assert os.path.exists(os.path.join(m.cache_mgr.cache_root, revision, "test1.txt")) is False
        assert os.path.exists(os.path.join(m.cache_mgr.cache_root, revision, "test2.txt")) is True
        assert os.path.exists(os.path.join(m.cache_mgr.cache_root, revision, "test3.txt")) is True
        assert os.path.exists(os.path.join(m.cache_mgr.cache_root, revision, "other_dir", "test3.txt")) is True
        assert os.path.exists(os.path.join(m.cache_mgr.cache_root, revision, "other_dir", "test1.txt")) is True

        query = """
                   mutation myMutation {
                     deleteDatasetFiles(input: {datasetOwner: "default", datasetName: "dataset-delete", 
                                                keys: ["test3.txt", "other_dir/"]}) {
                         success
                     }
                   }
                   """
        result = fixture_working_dir[2].execute(query)
        assert 'errors' not in result
        assert result['data']['deleteDatasetFiles']['success'] is True

        revision = m.dataset_revision
        assert os.path.exists(os.path.join(m.cache_mgr.cache_root, revision, "test1.txt")) is False
        assert os.path.exists(os.path.join(m.cache_mgr.cache_root, revision, "test2.txt")) is True
        assert os.path.exists(os.path.join(m.cache_mgr.cache_root, revision, "test3.txt")) is False
        assert os.path.exists(os.path.join(m.cache_mgr.cache_root, revision, "other_dir", "test3.txt")) is False
        assert os.path.exists(os.path.join(m.cache_mgr.cache_root, revision, "other_dir", "test1.txt")) is False

    def test_delete_dataset_files_errors(self, fixture_working_dir, snapshot):
        im = InventoryManager(fixture_working_dir[0])
        ds = im.create_dataset('default', 'default', "dataset-delete-2",
                               storage_type="gigantum_object_v1", description="testing delete")
        m = Manifest(ds, 'default')

        helper_append_file(m.cache_mgr.cache_root, m.dataset_revision, "test1.txt", "asdfadfsdf")
        helper_append_file(m.cache_mgr.cache_root, m.dataset_revision, "test2.txt", "fdsfgfd")
        m.sweep_all_changes()

        revision = m.dataset_revision
        assert os.path.exists(os.path.join(m.cache_mgr.cache_root, revision, "test1.txt")) is True
        assert os.path.exists(os.path.join(m.cache_mgr.cache_root, revision, "test2.txt")) is True

        query = """
                   mutation myMutation {
                     deleteDatasetFiles(input: {datasetOwner: "default", datasetName: "dataset-delete-2", 
                                                keys: ["testdfdfdfdf.txt"]}) {
                         success
                     }
                   }
                   """
        result = fixture_working_dir[2].execute(query)
        assert 'errors' in result

    def test_move_dataset_file(self, fixture_working_dir, snapshot):
        im = InventoryManager(fixture_working_dir[0])
        ds = im.create_dataset('default', 'default', "dataset-move",
                               storage_type="gigantum_object_v1", description="testing move")
        m = Manifest(ds, 'default')

        revision = m.dataset_revision
        helper_append_file(m.cache_mgr.cache_root, revision, "test1.txt", "asdfasdghndfdf")
        m.sweep_all_changes()

        revision = m.dataset_revision
        cr = m.cache_mgr.cache_root
        assert os.path.exists(os.path.join(cr, revision, "test1.txt")) is True

        query = """
                   mutation myMutation {
                     moveDatasetFile(input: {datasetOwner: "default", datasetName: "dataset-move", 
                                             srcPath: "test1.txt", dstPath: "test1-renamed.txt"}) {
                         updatedEdges {
                            node {
                              id
                              key
                              isDir
                              isLocal
                              size
                            }
                         }
                     }
                   }
                   """
        result = fixture_working_dir[2].execute(query)
        assert 'errors' not in result
        snapshot.assert_match(result)

        revision = m.dataset_revision
        cr = m.cache_mgr.cache_root
        assert os.path.exists(os.path.join(cr, revision, "test1.txt")) is False
        assert os.path.exists(os.path.join(cr, revision, "test1-renamed.txt")) is True

    def test_move_dataset_dir(self, fixture_working_dir, snapshot):
        im = InventoryManager(fixture_working_dir[0])
        ds = im.create_dataset('default', 'default', "dataset-move",
                               storage_type="gigantum_object_v1", description="testing move")
        m = Manifest(ds, 'default')

        revision = m.dataset_revision
        os.makedirs(os.path.join(m.cache_mgr.cache_root, revision, "first_dir"))
        os.makedirs(os.path.join(m.cache_mgr.cache_root, revision, "other_dir"))
        os.makedirs(os.path.join(m.cache_mgr.cache_root, revision, "other_dir", "nested_dir"))
        helper_append_file(m.cache_mgr.cache_root, revision, "test1.txt", "asdfasdghndfdf")
        helper_append_file(m.cache_mgr.cache_root, revision, "test2.txt", "asdfdf")
        helper_append_file(m.cache_mgr.cache_root, revision, "first_dir/test3.txt", "4456tyfg")
        helper_append_file(m.cache_mgr.cache_root, revision, "other_dir/nested_dir/test6.txt", "4456tyfg")
        helper_append_file(m.cache_mgr.cache_root, revision, "other_dir/nested_dir/test7.txt", "fgfyytr")
        m.sweep_all_changes()

        revision = m.dataset_revision
        cr = m.cache_mgr.cache_root
        assert os.path.exists(os.path.join(cr, revision, "test1.txt")) is True
        assert os.path.exists(os.path.join(cr, revision, "test2.txt")) is True
        assert os.path.exists(os.path.join(cr, revision, "first_dir", "test3.txt")) is True
        assert os.path.exists(os.path.join(cr, revision, "other_dir", "nested_dir", "test6.txt")) is True
        assert os.path.exists(os.path.join(cr, revision, "other_dir", "nested_dir", "test7.txt")) is True

        query = """
                   mutation myMutation {
                     moveDatasetFile(input: {datasetOwner: "default", datasetName: "dataset-move", 
                                             srcPath: "first_dir/", dstPath: "other_dir/first_dir/"}) {
                         updatedEdges {
                            node {
                              id
                              key
                              isDir
                              isLocal
                              size
                            }
                         }
                     }
                   }
                   """
        result = fixture_working_dir[2].execute(query)
        assert 'errors' not in result
        snapshot.assert_match(result)

        revision = m.dataset_revision
        cr = m.cache_mgr.cache_root
        assert os.path.exists(os.path.join(cr, revision, "test1.txt")) is True
        assert os.path.exists(os.path.join(cr, revision, "test2.txt")) is True
        assert os.path.exists(os.path.join(cr, revision, "first_dir", "test3.txt")) is False
        assert os.path.exists(os.path.join(cr, revision, "other_dir", "first_dir", "test3.txt")) is True
        assert os.path.exists(os.path.join(cr, revision, "other_dir", "nested_dir", "test6.txt")) is True
        assert os.path.exists(os.path.join(cr, revision, "other_dir", "nested_dir", "test7.txt")) is True

        query = """
                   mutation myMutation {
                     moveDatasetFile(input: {datasetOwner: "default", datasetName: "dataset-move", 
                                             srcPath: "other_dir/", dstPath: "other_dir_renamed/"}) {
                         updatedEdges {
                            node {
                              id
                              key
                              isDir
                              isLocal
                              size
                            }
                         }
                     }
                   }
                   """
        result = fixture_working_dir[2].execute(query)
        assert 'errors' not in result
        snapshot.assert_match(result)

        revision = m.dataset_revision
        cr = m.cache_mgr.cache_root
        assert os.path.exists(os.path.join(cr, revision, "test1.txt")) is True
        assert os.path.exists(os.path.join(cr, revision, "test2.txt")) is True
        assert os.path.exists(os.path.join(cr, revision, "other_dir", "first_dir", "test3.txt")) is False
        assert os.path.exists(os.path.join(cr, revision, "other_dir", "nested_dir", "test6.txt")) is False
        assert os.path.exists(os.path.join(cr, revision, "other_dir", "nested_dir", "test7.txt")) is False
        assert os.path.exists(os.path.join(cr, revision, "other_dir_renamed", "first_dir", "test3.txt")) is True
        assert os.path.exists(os.path.join(cr, revision, "other_dir_renamed", "nested_dir", "test6.txt")) is True
        assert os.path.exists(os.path.join(cr, revision, "other_dir_renamed", "nested_dir", "test7.txt")) is True

    def test_make_directory(self, fixture_working_dir, snapshot):
        im = InventoryManager(fixture_working_dir[0])
        ds = im.create_dataset('default', 'default', "dataset-dir",
                               storage_type="gigantum_object_v1", description="testing move")
        m = Manifest(ds, 'default')
        m.link_revision()

        query = """
                   mutation myMutation {
                     makeDatasetDirectory(input: {datasetOwner: "default", datasetName: "dataset-dir", 
                                             key: "test_dir1/"}) {
                         newDatasetFileEdge {
                            node {
                              id
                              key
                              isDir
                              isLocal
                              size
                            }
                         }
                     }
                   }
                   """
        result = fixture_working_dir[2].execute(query)
        assert 'errors' not in result
        assert result['data']['makeDatasetDirectory']['newDatasetFileEdge']['node']['key'] == 'test_dir1/'
        assert result['data']['makeDatasetDirectory']['newDatasetFileEdge']['node']['isDir'] is True
        assert result['data']['makeDatasetDirectory']['newDatasetFileEdge']['node']['isLocal'] is True
        assert result['data']['makeDatasetDirectory']['newDatasetFileEdge']['node']['size'] == '0'

        assert os.path.isdir(os.path.join(m.cache_mgr.current_revision_dir, "test_dir1")) is True

        query = """
                   mutation myMutation {
                     makeDatasetDirectory(input: {datasetOwner: "default", datasetName: "dataset-dir", 
                                             key: "test_dir1/test_dir2/"}) {
                         newDatasetFileEdge {
                            node {
                              id
                              key
                              isDir
                              isLocal
                              size
                            }
                         }
                     }
                   }
                   """
        result = fixture_working_dir[2].execute(query)
        assert 'errors' not in result
        assert result['data']['makeDatasetDirectory']['newDatasetFileEdge']['node']['key'] == 'test_dir1/test_dir2/'
        assert result['data']['makeDatasetDirectory']['newDatasetFileEdge']['node']['isDir'] is True
        assert result['data']['makeDatasetDirectory']['newDatasetFileEdge']['node']['isLocal'] is True
        assert result['data']['makeDatasetDirectory']['newDatasetFileEdge']['node']['size'] == '0'

        assert os.path.isdir(os.path.join(m.cache_mgr.current_revision_dir, "test_dir1")) is True
        assert os.path.isdir(os.path.join(m.cache_mgr.current_revision_dir, "test_dir1", "test_dir2")) is True

    def test_make_directory_error(self, fixture_working_dir, snapshot):
        im = InventoryManager(fixture_working_dir[0])
        ds = im.create_dataset('default', 'default', "dataset-dir",
                               storage_type="gigantum_object_v1", description="testing move")
        m = Manifest(ds, 'default')

        # Test where parent dir doesnt exists (because you need to create the parent)
        query = """
                   mutation myMutation {
                     makeDatasetDirectory(input: {datasetOwner: "default", datasetName: "dataset-dir", 
                                             key: "test_dir1/test_dir2/"}) {
                         newDatasetFileEdge {
                            node {
                              id
                              key
                              isDir
                              isLocal
                              size
                            }
                         }
                     }
                   }
                   """
        result = fixture_working_dir[2].execute(query)
        assert 'errors' in result
        assert 'Parent directory' in result['errors'][0]['message']

        # Test where missing trailing slash
        query = """
                   mutation myMutation {
                     makeDatasetDirectory(input: {datasetOwner: "default", datasetName: "dataset-dir", 
                                             key: "test_dir1"}) {
                         newDatasetFileEdge {
                            node {
                              id
                              key
                              isDir
                              isLocal
                              size
                            }
                         }
                     }
                   }
                   """
        result = fixture_working_dir[2].execute(query)
        assert 'errors' in result
        assert 'Provided relative path must end in' in result['errors'][0]['message']
