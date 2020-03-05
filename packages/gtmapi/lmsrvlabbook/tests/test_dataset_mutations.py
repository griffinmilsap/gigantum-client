import pytest
import os
import responses
import flask
from mock import patch
import shutil
import tempfile

from snapshottest import snapshot
from lmsrvlabbook.tests.fixtures import fixture_working_dir_env_repo_scoped, fixture_working_dir, \
    fixture_working_dir_dataset_tests, mock_enable_unmanaged_for_testing

from gtmcore.configuration.utils import call_subprocess
from gtmcore.dispatcher import Dispatcher
from gtmcore.inventory.inventory import InventoryManager
from gtmcore.dataset.manifest import Manifest

from gtmcore.fixtures.datasets import mock_dataset_with_cache_dir, mock_dataset_with_manifest, helper_append_file

from gtmcore.fixtures import _MOCK_create_remote_repo2


class TestDatasetMutations(object):
    def test_create_dataset(self, fixture_working_dir, snapshot):
        query = """
        mutation myCreateDataset($name: String!, $desc: String!, $storage_type: String!) {
          createDataset(input: {name: $name, description: $desc,
                                storageType: $storage_type}) {
            dataset {
              id
              name
              description
              schemaVersion
              datasetType{
                name
                id
                description
              }
            }
          }
        }
        """
        variables = {"name": "test-dataset-1", "desc": "my test dataset",
                     "storage_type": "gigantum_object_v1"}

        snapshot.assert_match(fixture_working_dir[2].execute(query, variable_values=variables))

        # Get Dataset you just created
        query = """{
            dataset(name: "test-dataset-1", owner: "default")  {
                  id
                  name
                  description
                  schemaVersion
                  datasetType{
                    name
                    id
                    description
                  }
                }
                }
        """
        snapshot.assert_match(fixture_working_dir[2].execute(query))

    def test_fetch_dataset_edge(self, fixture_working_dir):
        """Test export"""
        create_query = """
                mutation myCreateDataset($name: String!, $desc: String!, $storage_type: String!) {
                  createDataset(input: {name: $name, description: $desc,
                                        storageType: $storage_type}) {
                    dataset {
                      id
                      name
                    }
                  }
                }
                """
        create_variables = {"name": "test-dataset-2", "desc": "my test dataset",
                            "storage_type": "gigantum_object_v1"}

        result = fixture_working_dir[2].execute(create_query, variable_values=create_variables)
        assert "errors" not in result

        query = """
                mutation myMutation($owner: String!, $datasetName: String!) {
                  fetchDatasetEdge(input: {owner: $owner, datasetName: $datasetName}) {
                      newDatasetEdge {
                        node {
                          id
                          name
                        }
                      }
                  }
                }
                """
        variables = {"datasetName": "test-dataset-2", "owner": "default"}
        result = fixture_working_dir[2].execute(query, variable_values=variables)
        assert "errors" not in result
        assert "test-dataset-2" == result['data']['fetchDatasetEdge']['newDatasetEdge']['node']['name']

    def test_modify_dataset_link(self, fixture_working_dir, snapshot):
        im = InventoryManager(fixture_working_dir[0])
        lb = im.create_labbook('default', 'default', 'test-lb', 'testing dataset links')
        ds = im.create_dataset('default', 'default', "dataset100", storage_type="gigantum_object_v1", description="100")

        # Fake publish to a local bare repo
        _MOCK_create_remote_repo2(ds, 'default', None, None)

        assert os.path.exists(os.path.join(lb.root_dir, '.gitmodules')) is False

        query = """
                   mutation myMutation($lo: String!, $ln: String!, $do: String!, $dn: String!,
                                       $a: String!, $du: String) {
                     modifyDatasetLink(input: {labbookOwner: $lo, labbookName: $ln, datasetOwner: $do, datasetName: $dn,
                                               action: $a, datasetUrl: $du}) {
                         newLabbookEdge {
                           node {
                             id
                             name
                             description
                             linkedDatasets {
                               name
                             }
                           }
                         }
                     }
                   }
                   """
        variables = {"lo": "default", "ln": "test-lb", "do": "default", "dn": "dataset100", "a": "link", "du": ds.remote}
        result = fixture_working_dir[2].execute(query, variable_values=variables)
        assert "errors" not in result
        snapshot.assert_match(result)

        assert os.path.exists(os.path.join(lb.root_dir, '.gitmodules')) is True
        dataset_submodule_dir = os.path.join(lb.root_dir, '.gigantum', 'datasets', 'default', 'dataset100')
        assert os.path.exists(dataset_submodule_dir) is True
        assert os.path.exists(os.path.join(dataset_submodule_dir, '.gigantum')) is True

        with open(os.path.join(lb.root_dir, '.gitmodules'), 'rt') as mf:
            data = mf.read()

        assert len(data) > 0

        query = """
                   mutation myMutation($lo: String!, $ln: String!, $do: String!, $dn: String!,
                                       $a: String!) {
                     modifyDatasetLink(input: {labbookOwner: $lo, labbookName: $ln, datasetOwner: $do, datasetName: $dn,
                                               action: $a}) {
                         newLabbookEdge {
                           node {
                             id
                             name
                             description
                             linkedDatasets {
                               name
                             }
                           }
                         }
                     }
                   }
                   """
        variables = {"lo": "default", "ln": "test-lb", "do": "default", "dn": "dataset100", "a": "unlink"}
        result = fixture_working_dir[2].execute(query, variable_values=variables)
        assert "errors" not in result
        snapshot.assert_match(result)

        dataset_submodule_dir = os.path.join(lb.root_dir, '.gigantum', 'datasets', 'default', 'dataset100')
        assert os.path.exists(dataset_submodule_dir) is False
        assert os.path.exists(os.path.join(dataset_submodule_dir, '.gigantum')) is False
        with open(os.path.join(lb.root_dir, '.gitmodules'), 'rt') as mf:
            data = mf.read()

        assert len(data) == 0

    def test_modify_dataset_link_errors(self, fixture_working_dir, snapshot):
        im = InventoryManager(fixture_working_dir[0])
        lb = im.create_labbook('default', 'default', 'test-lb', 'testing dataset links')
        ds = im.create_dataset('default', 'default', "dataset100", storage_type="gigantum_object_v1",
                               description="100")
        # Fake publish to a local bare repo
        _MOCK_create_remote_repo2(ds, 'default', None, None)

        query = """
                   mutation myMutation($lo: String!, $ln: String!, $do: String!, $dn: String!,
                                       $a: String!, $du: String) {
                     modifyDatasetLink(input: {labbookOwner: $lo, labbookName: $ln, datasetOwner: $do, datasetName: $dn,
                                               action: $a, datasetUrl: $du}) {
                         newLabbookEdge {
                           node {
                             id
                             name
                             description
                             linkedDatasets {
                               name
                             }
                           }
                         }
                     }
                   }
                   """
        variables = {"lo": "default", "ln": "test-lb", "do": "default", "dn": "dataset100", "a": "asdfasdf",
                     "du": ds.remote}
        result = fixture_working_dir[2].execute(query, variable_values=variables)
        assert "errors" in result
        snapshot.assert_match(result)

    def test_modify_dataset_link_local(self, fixture_working_dir):
        im = InventoryManager(fixture_working_dir[0])
        lb = im.create_labbook('default', 'default', 'test-lb', 'testing dataset links')
        ds = im.create_dataset('default', 'default', "dataset100", storage_type="gigantum_object_v1", description="100")

        assert os.path.exists(os.path.join(lb.root_dir, '.gitmodules')) is False

        query = """
                   mutation myMutation($lo: String!, $ln: String!, $do: String!, $dn: String!,
                                       $a: String!) {
                     modifyDatasetLink(input: {labbookOwner: $lo, labbookName: $ln, datasetOwner: $do, datasetName: $dn,
                                               action: $a}) {
                         newLabbookEdge {
                           node {
                             id
                             name
                             description
                             linkedDatasets {
                               name
                               defaultRemote
                             }
                           }
                         }
                     }
                   }
                   """
        variables = {"lo": "default", "ln": "test-lb", "do": "default", "dn": "dataset100", "a": "link"}
        result = fixture_working_dir[2].execute(query, variable_values=variables)
        assert "errors" not in result
        assert result['data']['modifyDatasetLink']['newLabbookEdge']['node']['name'] == 'test-lb'
        assert len(result['data']['modifyDatasetLink']['newLabbookEdge']['node']['linkedDatasets']) == 1
        assert result['data']['modifyDatasetLink']['newLabbookEdge']['node']['linkedDatasets'][0]['name'] == 'dataset100'
        assert '.git' in result['data']['modifyDatasetLink']['newLabbookEdge']['node']['linkedDatasets'][0]['defaultRemote']

        assert os.path.exists(os.path.join(lb.root_dir, '.gitmodules')) is True
        dataset_submodule_dir = os.path.join(lb.root_dir, '.gigantum', 'datasets', 'default', 'dataset100')
        assert os.path.exists(dataset_submodule_dir) is True
        assert os.path.exists(os.path.join(dataset_submodule_dir, '.gigantum')) is True

        with open(os.path.join(lb.root_dir, '.gitmodules'), 'rt') as mf:
            data = mf.read()

        assert len(data) > 0

        query = """
                   mutation myMutation($lo: String!, $ln: String!, $do: String!, $dn: String!,
                                       $a: String!) {
                     modifyDatasetLink(input: {labbookOwner: $lo, labbookName: $ln, datasetOwner: $do, datasetName: $dn,
                                               action: $a}) {
                         newLabbookEdge {
                           node {
                             id
                             name
                             description
                             linkedDatasets {
                               name
                             }
                           }
                         }
                     }
                   }
                   """
        variables = {"lo": "default", "ln": "test-lb", "do": "default", "dn": "dataset100", "a": "unlink"}
        result = fixture_working_dir[2].execute(query, variable_values=variables)
        assert "errors" not in result
        assert result['data']['modifyDatasetLink']['newLabbookEdge']['node']['name'] == 'test-lb'
        assert len(result['data']['modifyDatasetLink']['newLabbookEdge']['node']['linkedDatasets']) == 0

        dataset_submodule_dir = os.path.join(lb.root_dir, '.gigantum', 'datasets', 'default', 'dataset100')
        assert os.path.exists(dataset_submodule_dir) is False
        assert os.path.exists(os.path.join(dataset_submodule_dir, '.gigantum')) is False
        with open(os.path.join(lb.root_dir, '.gitmodules'), 'rt') as mf:
            data = mf.read()

        assert len(data) == 0

    def test_set_dataset_description(self, fixture_working_dir):
        create_query = """
                mutation myCreateDataset($name: String!, $desc: String!, $storage_type: String!) {
                  createDataset(input: {name: $name, description: $desc,
                                        storageType: $storage_type}) {
                    dataset {
                      id
                      name
                    }
                  }
                }
                """
        create_variables = {"name": "test-dataset-55", "desc": "starting description",
                            "storage_type": "gigantum_object_v1"}
        result = fixture_working_dir[2].execute(create_query, variable_values=create_variables)
        assert "errors" not in result

        query = """
                mutation myMutation($owner: String!, $datasetName: String!, $desc: String!) {
                  setDatasetDescription(input: {owner: $owner, datasetName: $datasetName, description: $desc}) {
                      updatedDataset {
                          id
                          name
                          description
                      }
                  }
                }
                """
        variables = {"datasetName": "test-dataset-55", "owner": "default", "desc": "updated description"}
        result = fixture_working_dir[2].execute(query, variable_values=variables)
        assert "errors" not in result
        assert "test-dataset-55" == result['data']['setDatasetDescription']['updatedDataset']['name']
        assert "updated description" == result['data']['setDatasetDescription']['updatedDataset']['description']

        query = """{
                    dataset(name: "test-dataset-55", owner: "default") {
                      id
                      name
                      description
                    }
                    }
                """
        result = fixture_working_dir[2].execute(query, variable_values=variables)
        assert "errors" not in result
        assert result['data']['dataset']['description'] == "updated description"
        assert result['data']['dataset']['name'] == "test-dataset-55"

    def test_write_dataset_readme(self, fixture_working_dir):
        create_query = """
                mutation myCreateDataset($name: String!, $desc: String!, $storage_type: String!) {
                  createDataset(input: {name: $name, description: $desc,
                                        storageType: $storage_type}) {
                    dataset {
                      id
                      name
                    }
                  }
                }
                """
        create_variables = {"name": "test-dataset-35", "desc": "starting description",
                            "storage_type": "gigantum_object_v1"}
        result = fixture_working_dir[2].execute(create_query, variable_values=create_variables)
        assert "errors" not in result

        query = """
                mutation myMutation($owner: String!, $datasetName: String!, $content: String!) {
                  writeDatasetReadme(input: {owner: $owner, datasetName: $datasetName, content: $content}) {
                      updatedDataset {
                          id
                          name
                          overview {
                            readme
                        }
                      }
                  }
                }
                """
        variables = {"datasetName": "test-dataset-35", "owner": "default", "content": "##My readme\nthis thing"}
        result = fixture_working_dir[2].execute(query, variable_values=variables)
        assert "errors" not in result
        assert "test-dataset-35" == result['data']['writeDatasetReadme']['updatedDataset']['name']
        assert "##My readme\nthis thing" == result['data']['writeDatasetReadme']['updatedDataset']['overview']['readme']

        query = """{
                    dataset(name: "test-dataset-35", owner: "default") {
                          id
                          name
                          overview {
                            readme
                        }
                    }
                    }
                """
        result = fixture_working_dir[2].execute(query, variable_values=variables)
        assert "errors" not in result
        assert result['data']['dataset']['overview']['readme'] == "##My readme\nthis thing"
        assert result['data']['dataset']['name'] == "test-dataset-35"

    def test_delete_local_dataset(self, fixture_working_dir):
        class JobResponseMock(object):
            def __init__(self, key):
                self.key_str = key

        def dispatcher_mock(self, function_ref, kwargs, metadata):
            assert kwargs['logged_in_username'] == 'default'
            assert kwargs['dataset_owner'] == 'default'
            assert kwargs['dataset_name'] == 'dataset100'
            assert ".labmanager/datasets/default/default/dataset100" in kwargs['cache_location']
            assert metadata['method'] == 'clean_dataset_file_cache'

            return JobResponseMock("rq:job:00923477-d46b-479c-ad0c-2b66fdfdfb6b10")

        im = InventoryManager(fixture_working_dir[0])
        ds = im.create_dataset('default', 'default', "dataset100", storage_type="gigantum_object_v1", description="100")
        dataset_dir = ds.root_dir
        assert os.path.exists(dataset_dir) is True

        query = """
                mutation myMutation($owner: String!, $datasetName: String!) {
                  deleteDataset(input: {owner: $owner, datasetName: $datasetName, local: true, remote: false}) {
                      localDeleted
                      remoteDeleted
                  }
                }
                """
        variables = {"datasetName": "dataset100", "owner": "default"}

        with patch.object(Dispatcher, 'dispatch_task', dispatcher_mock):
            result = fixture_working_dir[2].execute(query, variable_values=variables)

        assert "errors" not in result
        assert result['data']['deleteDataset']['localDeleted'] is True
        assert result['data']['deleteDataset']['remoteDeleted'] is False

        assert os.path.exists(dataset_dir) is False

    @responses.activate
    def test_delete_remote_dataset(self, fixture_working_dir):
        responses.add(responses.POST, 'https://gigantum.com/api/v1',
                      json={'data': {'additionalCredentials': {'gitServiceToken': 'afaketoken'}}}, status=200)
        responses.add(responses.GET, 'https://repo.gigantum.io/api/v4/projects/default%2Fdataset100',
                      json=[{
                              "id": 27,
                              "description": "",
                            }],
                      status=200)
        responses.add(responses.DELETE, 'https://repo.gigantum.io/api/v4/projects/default%2Fdataset100',
                      json={
                                "message": "202 Accepted"
                            },
                      status=202)
        responses.add(responses.GET, 'https://repo.gigantum.io/api/v4/projects/default%2Fdataset100',
                      json=[{
                                "message": "404 Project Not Found"
                            }],
                      status=404)
        responses.add(responses.DELETE, 'https://api.gigantum.com/read/index/default%2Fdataset100',
                      json=[{
                                "message": "success"
                            }],
                      status=204)
        responses.add(responses.DELETE, 'https://api.gigantum.com/object-v1/default/dataset100',
                      json=[{'status': 'queueing for delete'}],
                      status=200)

        im = InventoryManager(fixture_working_dir[0])
        ds = im.create_dataset('default', 'default', "dataset100", storage_type="gigantum_object_v1", description="100")
        dataset_dir = ds.root_dir
        assert os.path.exists(dataset_dir) is True

        query = """
                mutation myMutation($owner: String!, $datasetName: String!) {
                  deleteDataset(input: {owner: $owner, datasetName: $datasetName, local: false, remote: true}) {
                      localDeleted
                      remoteDeleted
                  }
                }
                """
        variables = {"datasetName": "dataset100", "owner": "default"}
        result = fixture_working_dir[2].execute(query, variable_values=variables)
        assert "errors" not in result
        assert result['data']['deleteDataset']['localDeleted'] is False
        assert result['data']['deleteDataset']['remoteDeleted'] is True

        assert os.path.exists(dataset_dir) is True

    @responses.activate
    def test_delete_remote_dataset_not_local(self, fixture_working_dir):
        query = """
                mutation myMutation($owner: String!, $datasetName: String!) {
                  deleteDataset(input: {owner: $owner, datasetName: $datasetName, local: false, remote: true}) {
                      localDeleted
                      remoteDeleted
                  }
                }
                """
        variables = {"datasetName": "dataset100", "owner": "default"}
        result = fixture_working_dir[2].execute(query, variable_values=variables)
        assert "errors" in result
        assert result['errors'][0]['message'] == "A dataset must exist locally to delete it in the remote."

    @responses.activate
    def test_delete_remote_dataset_no_session(self, fixture_working_dir):
        im = InventoryManager(fixture_working_dir[0])
        ds = im.create_dataset('default', 'default', "dataset100", storage_type="gigantum_object_v1", description="100")
        dataset_dir = ds.root_dir
        assert os.path.exists(dataset_dir) is True

        flask.g.access_token = None
        flask.g.id_token = None

        query = """
                mutation myMutation($owner: String!, $datasetName: String!) {
                  deleteDataset(input: {owner: $owner, datasetName: $datasetName, local: false, remote: true}) {
                      localDeleted
                      remoteDeleted
                  }
                }
                """
        variables = {"datasetName": "dataset100", "owner": "default"}
        result = fixture_working_dir[2].execute(query, variable_values=variables)
        assert "errors" in result
        assert "requires a valid session" in result['errors'][0]['message']

    @responses.activate
    def test_delete_remote_dataset_gitlab_error(self, fixture_working_dir):
        responses.add(responses.POST, 'https://gigantum.com/api/v1',
                      json={'data': {'additionalCredentials': {'gitServiceToken': 'afaketoken'}}}, status=200)
        responses.add(responses.GET, 'https://repo.gigantum.io/api/v4/projects/default%2Fdataset100',
                      json=[{
                              "id": 27,
                              "description": "",
                            }],
                      status=200)

        responses.add(responses.DELETE, 'https://api.gigantum.com/object-v1/default/dataset100',
                      json=[{'status': 'queueing for delete'}],
                      status=200)

        responses.add(responses.DELETE, 'https://repo.gigantum.io/api/v4/projects/default%2Fdataset100',
                      json={
                                "message": "fail"
                            },
                      status=400)

        im = InventoryManager(fixture_working_dir[0])
        ds = im.create_dataset('default', 'default', "dataset100", storage_type="gigantum_object_v1", description="100")
        dataset_dir = ds.root_dir
        assert os.path.exists(dataset_dir) is True

        query = """
                mutation myMutation($owner: String!, $datasetName: String!) {
                  deleteDataset(input: {owner: $owner, datasetName: $datasetName, local: false, remote: true}) {
                      localDeleted
                      remoteDeleted
                  }
                }
                """
        variables = {"datasetName": "dataset100", "owner": "default"}
        result = fixture_working_dir[2].execute(query, variable_values=variables)
        assert "errors" in result
        assert result['errors'][0]['message'] == "Failed to remove remote repository"

        assert os.path.exists(dataset_dir) is True

    def test_configure_local(self, fixture_working_dir_dataset_tests, snapshot):
        im = InventoryManager(fixture_working_dir_dataset_tests[0])
        ds = im.create_dataset('default', 'default', "adataset", storage_type="local_filesystem", description="100")
        dataset_dir = ds.root_dir
        assert os.path.exists(dataset_dir) is True

        query = """
                   {
                      dataset(owner: "default", name: "adataset"){
                        backendIsConfigured
                        backendConfiguration{
                          parameter
                          description
                          parameterType
                          value
                        }
                      }
                   }
                """
        result = fixture_working_dir_dataset_tests[2].execute(query)
        assert "errors" not in result
        snapshot.assert_match(result)

        query = """
                    mutation myMutation{
                      configureDataset(input: {datasetOwner: "default", datasetName: "adataset",
                        parameters: [{parameter: "Data Directory", parameterType: "str", value: "doesnotexist"}]}) {
                          isConfigured
                          shouldConfirm
                          errorMessage
                          confirmMessage
                          hasBackgroundJob
                          backgroundJobKey
                      }
                    }
                """
        result = fixture_working_dir_dataset_tests[2].execute(query)
        assert "errors" not in result
        snapshot.assert_match(result)

        # Create dir to fix validation issue
        os.makedirs(os.path.join(fixture_working_dir_dataset_tests[1], 'local_data', 'test_local_dir'))

        query = """
                    mutation myMutation{
                      configureDataset(input: {datasetOwner: "default", datasetName: "adataset",
                        parameters: [{parameter: "Data Directory", parameterType: "str", value: "test_local_dir"}]}) {
                          isConfigured
                          shouldConfirm
                          errorMessage
                          confirmMessage
                          hasBackgroundJob
                          backgroundJobKey
                      }
                    }
                """
        result = fixture_working_dir_dataset_tests[2].execute(query)
        assert "errors" not in result
        snapshot.assert_match(result)

        query = """
                    mutation myMutation{
                      configureDataset(input: {datasetOwner: "default", datasetName: "adataset", confirm: true}) {
                          isConfigured
                          shouldConfirm
                          errorMessage
                          confirmMessage
                          hasBackgroundJob
                          backgroundJobKey
                      }
                    }
                """
        result = fixture_working_dir_dataset_tests[2].execute(query)
        assert "errors" not in result
        assert "rq:job" in result['data']['configureDataset']['backgroundJobKey']
        assert result['data']['configureDataset']['isConfigured'] is True

    def test_update_unmanaged_dataset_local_errors(self, fixture_working_dir_dataset_tests):
        im = InventoryManager(fixture_working_dir_dataset_tests[0])
        ds = im.create_dataset('default', 'default', "adataset", storage_type="local_filesystem", description="100")
        dataset_dir = ds.root_dir
        assert os.path.exists(dataset_dir) is True

        query = """
                    mutation myMutation{
                      updateUnmanagedDataset(input: {datasetOwner: "default", datasetName: "adataset"}) {
                          backgroundJobKey
                      }
                    }
                """
        result = fixture_working_dir_dataset_tests[2].execute(query)
        assert "errors" in result

        # not configured
        query = """
                    mutation myMutation{
                      updateUnmanagedDataset(input: {datasetOwner: "default", datasetName: "adataset",
                       fromLocal: true}) {
                          backgroundJobKey
                      }
                    }
                """
        result = fixture_working_dir_dataset_tests[2].execute(query)
        assert "errors" in result

    def test_update_unmanaged_dataset_local(self, fixture_working_dir_dataset_tests):
        im = InventoryManager(fixture_working_dir_dataset_tests[0])
        ds = im.create_dataset('default', 'default', "adataset", storage_type="local_filesystem", description="100")
        dataset_dir = ds.root_dir
        assert os.path.exists(dataset_dir) is True

        # configure backend and local dir
        working_dir = fixture_working_dir_dataset_tests[1]
        ds.backend.set_default_configuration('default', 'asdf', '1234')
        current_config = ds.backend_config
        current_config['Data Directory'] = "test_dir"
        ds.backend_config = current_config
        test_dir = os.path.join(working_dir, "local_data", "test_dir")
        os.makedirs(test_dir)
        with open(os.path.join(test_dir, "test.txt"), 'wt') as temp:
            temp.write(f'dummy data: asdfasdf')

        query = """
                    mutation myMutation{
                      updateUnmanagedDataset(input: {datasetOwner: "default", datasetName: "adataset",
                       fromLocal: true}) {
                          backgroundJobKey
                      }
                    }
                """
        result = fixture_working_dir_dataset_tests[2].execute(query)
        assert "errors" not in result
        assert "rq:job" in result['data']['updateUnmanagedDataset']['backgroundJobKey']

    def test_update_unmanaged_dataset_remote(self, fixture_working_dir_dataset_tests):
        im = InventoryManager(fixture_working_dir_dataset_tests[0])
        ds = im.create_dataset('default', 'default', "adataset", storage_type="local_filesystem", description="100")
        dataset_dir = ds.root_dir
        assert os.path.exists(dataset_dir) is True

        # configure backend and local dir
        working_dir = fixture_working_dir_dataset_tests[1]
        ds.backend.set_default_configuration('default', 'asdf', '1234')
        current_config = ds.backend_config
        current_config['Data Directory'] = "test_dir"
        ds.backend_config = current_config
        test_dir = os.path.join(working_dir, "local_data", "test_dir")
        os.makedirs(test_dir)
        with open(os.path.join(test_dir, "test.txt"), 'wt') as temp:
            temp.write(f'dummy data: asdfasdf')

        query = """
                    mutation myMutation{
                      updateUnmanagedDataset(input: {datasetOwner: "default", datasetName: "adataset",
                       fromRemote: true}) {
                          backgroundJobKey
                      }
                    }
                """
        result = fixture_working_dir_dataset_tests[2].execute(query)
        assert "errors" not in result
        assert "rq:job" in result['data']['updateUnmanagedDataset']['backgroundJobKey']

    def test_verify_unmanaged_dataset(self, fixture_working_dir_dataset_tests):
        im = InventoryManager(fixture_working_dir_dataset_tests[0])
        ds = im.create_dataset('default', 'default', "adataset", storage_type="local_filesystem", description="100")
        dataset_dir = ds.root_dir
        assert os.path.exists(dataset_dir) is True

        # configure backend and local dir
        working_dir = fixture_working_dir_dataset_tests[1]
        ds.backend.set_default_configuration('default', 'asdf', '1234')
        current_config = ds.backend_config
        current_config['Data Directory'] = "test_dir"
        ds.backend_config = current_config
        test_dir = os.path.join(working_dir, "local_data", "test_dir")
        os.makedirs(test_dir)
        with open(os.path.join(test_dir, "test.txt"), 'wt') as temp:
            temp.write(f'dummy data: asdfasdf')

        query = """
                    mutation myMutation{
                      verifyDataset(input: {datasetOwner: "default", datasetName: "adataset"}) {
                          backgroundJobKey
                      }
                    }
                """
        result = fixture_working_dir_dataset_tests[2].execute(query)
        assert "errors" not in result
        assert "rq:job" in result['data']['verifyDataset']['backgroundJobKey']

    def test_update_dataset_link(self, fixture_working_dir, snapshot):
        im = InventoryManager(fixture_working_dir[0])
        lb = im.create_labbook('default', 'default', 'test-lb', 'testing dataset links')
        ds = im.create_dataset('default', 'default', "dataset100", storage_type="gigantum_object_v1", description="100")
        manifest = Manifest(ds, 'default')
        helper_append_file(manifest.cache_mgr.cache_root, manifest.dataset_revision,
                           "test1.txt", "12345")
        manifest.sweep_all_changes()

        # Fake publish to a local bare repo
        _MOCK_create_remote_repo2(ds, 'default', None, None)

        assert os.path.exists(os.path.join(lb.root_dir, '.gitmodules')) is False

        overview_query = """
                {
                  labbook(owner: "default", name:"test-lb")
                  {
                    linkedDatasets{
                      name
                      overview {
                          localBytes
                          totalBytes
                      }
                    }
                  }
                }
                """

        query = """
                   mutation myMutation($lo: String!, $ln: String!, $do: String!, $dn: String!,
                                       $a: String!, $du: String) {
                     modifyDatasetLink(input: {labbookOwner: $lo, labbookName: $ln, datasetOwner: $do, datasetName: $dn,
                                               action: $a, datasetUrl: $du}) {
                         newLabbookEdge {
                           node {
                             id
                             name
                             description
                             linkedDatasets {
                               name
                             }
                           }
                         }
                     }
                   }
                   """
        variables = {"lo": "default", "ln": "test-lb", "do": "default", "dn": "dataset100", "a": "link", "du": ds.remote}
        result = fixture_working_dir[2].execute(query, variable_values=variables)
        assert "errors" not in result
        snapshot.assert_match(result)

        assert os.path.exists(os.path.join(lb.root_dir, '.gitmodules')) is True
        dataset_submodule_dir = os.path.join(lb.root_dir, '.gigantum', 'datasets', 'default', 'dataset100')
        assert os.path.exists(dataset_submodule_dir) is True
        assert os.path.exists(os.path.join(dataset_submodule_dir, '.gigantum')) is True
        assert os.path.exists(os.path.join(dataset_submodule_dir, 'test_file.dat')) is False

        with open(os.path.join(lb.root_dir, '.gitmodules'), 'rt') as mf:
            data = mf.read()
        assert len(data) > 0

        # check overview
        result = fixture_working_dir[2].execute(overview_query)
        assert "errors" not in result
        assert result['data']['labbook']['linkedDatasets'][0]['overview']['localBytes'] == '5'
        assert result['data']['labbook']['linkedDatasets'][0]['overview']['totalBytes'] == '5'

        # Make change to published dataset
        git_dir = os.path.join(tempfile.gettempdir(), 'test_update_dataset_link_mutation')
        try:
            os.makedirs(git_dir)
            call_subprocess(['git', 'clone', ds.remote], cwd=git_dir, check=True)
            with open(os.path.join(git_dir, ds.name, 'test_file.dat'), 'wt') as tf:
                tf.write("Test File Contents")
            call_subprocess(['git', 'add', 'test_file.dat'], cwd=os.path.join(git_dir, ds.name), check=True)
            call_subprocess(['git', 'commit', '-m', 'editing repo'], cwd=os.path.join(git_dir, ds.name), check=True)
            call_subprocess(['git', 'push'], cwd=os.path.join(git_dir, ds.name), check=True)

            query = """
                       mutation myMutation($lo: String!, $ln: String!, $do: String!, $dn: String!,
                                           $a: String!) {
                         modifyDatasetLink(input: {labbookOwner: $lo, labbookName: $ln, datasetOwner: $do, datasetName: $dn,
                                                   action: $a}) {
                             newLabbookEdge {
                               node {
                                 id
                                 name
                                 description
                                 linkedDatasets {
                                   name
                                 }
                               }
                             }
                         }
                       }
                       """
            variables = {"lo": "default", "ln": "test-lb", "do": "default", "dn": "dataset100", "a": "update"}
            result = fixture_working_dir[2].execute(query, variable_values=variables)
            assert "errors" not in result
            snapshot.assert_match(result)

            # verify change is reflected
            assert os.path.exists(os.path.join(dataset_submodule_dir, 'test_file.dat')) is True

            # Verify activity record
            assert "Updated Dataset `default/dataset100` link to version" in lb.git.log()[0]['message']

        finally:
            if os.path.exists(git_dir):
                shutil.rmtree(git_dir)
