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
import os
import json
from mock import patch

from gtmcore.fixtures import ENV_UNIT_TEST_REPO, ENV_UNIT_TEST_BASE, ENV_UNIT_TEST_REV

from snapshottest import snapshot
from lmsrvlabbook.tests.fixtures import fixture_working_dir_env_repo_scoped, fixture_working_dir
from gtmcore.dispatcher import Dispatcher

import pytest
from gtmcore.files import FileOperations
from gtmcore.fixtures import remote_labbook_repo, mock_config_file, flush_redis_repo_cache

from gtmcore.inventory.inventory import InventoryManager


@pytest.fixture()
def mock_create_labbooks(fixture_working_dir):
    # Create a labbook in the temporary directory
    # Create a temporary labbook
    lb = InventoryManager(fixture_working_dir[0]).create_labbook("default", "default", "labbook1",
                                                                 description="Cats labbook 1")

    # Create a file in the dir
    with open(os.path.join(fixture_working_dir[1], 'sillyfile'), 'w') as sf:
        sf.write("1234567")
        sf.seek(0)
    FileOperations.insert_file(lb, 'code', sf.name)

    assert os.path.isfile(os.path.join(lb.root_dir, 'code', 'sillyfile'))
    # name of the config file, temporary working directory, the schema
    yield fixture_working_dir


class TestLabBookServiceMutations(object):
    def test_create_labbook(self, fixture_working_dir_env_repo_scoped, snapshot):
        """Test listing labbooks"""
        # Mock the configuration class it it returns the same mocked config file
        # Create LabBook
        query = """
        mutation myCreateLabbook($name: String!, $desc: String!, $repository: String!, 
                                 $base_id: String!, $revision: Int!) {
          createLabbook(input: {name: $name, description: $desc, 
                                repository: $repository, 
                                baseId: $base_id, revision: $revision}) {
            labbook {
              id
              name
              description
            }
          }
        }
        """
        variables = {"name": "test-lab-book1", "desc": "my test description",
                     "base_id": ENV_UNIT_TEST_BASE, "repository": ENV_UNIT_TEST_REPO,
                     "revision": ENV_UNIT_TEST_REV}
        snapshot.assert_match(fixture_working_dir_env_repo_scoped[2].execute(query, variable_values=variables))

        # Get LabBook you just created
        query = """
        {
          labbook(name: "test-lab-book1", owner: "default") {               
            activityRecords {
                edges{
                    node{
                        message
                        type
                        show
                        importance
                        tags
                        username
                        email
                        detailObjects{
                            type
                            data
                            show
                            importance
                            tags
                        }
                        }                        
                    }    
            }
          }
        }
        """
        snapshot.assert_match(fixture_working_dir_env_repo_scoped[2].execute(query))

    def test_delete_labbook(self, mock_create_labbooks, fixture_working_dir_env_repo_scoped):
        """Test deleting a LabBook off disk. """
        labbook_dir = os.path.join(mock_create_labbooks[1], 'default', 'default', 'labbooks', 'labbook1')

        assert os.path.exists(labbook_dir)

        delete_query = f"""
        mutation delete {{
            deleteLabbook(input: {{
                owner: "default",
                labbookName: "labbook1",
                confirm: true
            }}) {{
                success
            }}
        }}
        """

        r = fixture_working_dir_env_repo_scoped[2].execute(delete_query)
        assert 'errors' not in r
        assert r['data']['deleteLabbook']['success'] is True
        assert not os.path.exists(labbook_dir)

    def test_delete_labbook_with_linked_dataset_exists(self, fixture_working_dir_env_repo_scoped):
        """Test deleting a LabBook with a linked dataset, while the dataset still exists (shouldn't clean up)"""
        def dispatcher_mock(self, function_ref, kwargs, metadata):
            # If you get here, a cleanup job was scheduled, which shouldn't have happened since dataset still there
            assert "CLEANUP SHOULD NOT HAVE BEEN SCHEDULED"

        im = InventoryManager(fixture_working_dir_env_repo_scoped[0])
        lb = im.create_labbook("default", "default", "labbook1", description="Cats labbook 1")
        lb_root_dir = lb.root_dir
        assert os.path.exists(lb_root_dir)

        ds = im.create_dataset('default', 'default', "dataset2", storage_type="gigantum_object_v1", description="test")
        im.link_dataset_to_labbook(f"{ds.root_dir}/.git", "default", "dataset2", lb)

        delete_query = f"""
        mutation delete {{
            deleteLabbook(input: {{
                owner: "default",
                labbookName: "labbook1",
                confirm: true
            }}) {{
                success
            }}
        }}
        """
        with patch.object(Dispatcher, 'dispatch_task', dispatcher_mock):
            r = fixture_working_dir_env_repo_scoped[2].execute(delete_query)

        assert 'errors' not in r
        assert r['data']['deleteLabbook']['success'] is True
        assert not os.path.exists(lb_root_dir)
        assert os.path.exists(ds.root_dir)

    def test_delete_labbook_with_linked_dataset(self, fixture_working_dir_env_repo_scoped):
        """Test deleting a LabBook with a linked dataset that has been deleted as well, should clean up"""
        class JobResponseMock(object):
            def __init__(self, key):
                self.key_str = key

        def dispatcher_mock(self, function_ref, kwargs, metadata):
            assert kwargs['logged_in_username'] == 'default'
            assert kwargs['dataset_owner'] == 'default'
            assert kwargs['dataset_name'] == 'dataset22'
            assert ".labmanager/datasets/default/default/dataset22" in kwargs['cache_location']
            assert metadata['method'] == 'clean_dataset_file_cache'

            with open("/tmp/mock_reached", 'wt') as tf:
                tf.write("reached")

            return JobResponseMock("rq:job:00923477-d46b-479c-ad0c-2dffcfdfb6b10")

        im = InventoryManager(fixture_working_dir_env_repo_scoped[0])
        lb = im.create_labbook("default", "default", "labbook1", description="Cats labbook 1")
        lb_root_dir = lb.root_dir
        assert os.path.exists(lb_root_dir)
        assert os.path.exists("/tmp/mock_reached") is False

        ds = im.create_dataset('default', 'default', "dataset22", storage_type="gigantum_object_v1", description="test")
        ds_root_dir = ds.root_dir
        im.link_dataset_to_labbook(f"{ds.root_dir}/.git", "default", "dataset22", lb)
        im.delete_dataset('default', 'default', "dataset22")

        delete_query = f"""
        mutation delete {{
            deleteLabbook(input: {{
                owner: "default",
                labbookName: "labbook1",
                confirm: true
            }}) {{
                success
            }}
        }}
        """
        try:
            with patch.object(Dispatcher, 'dispatch_task', dispatcher_mock):
                r = fixture_working_dir_env_repo_scoped[2].execute(delete_query)

            assert 'errors' not in r
            assert r['data']['deleteLabbook']['success'] is True
            assert not os.path.exists(lb_root_dir)
            assert not os.path.exists(ds_root_dir)
            assert os.path.exists("/tmp/mock_reached") is True
        finally:
            if os.path.exists("/tmp/mock_reached"):
                os.remove("/tmp/mock_reached")

    def test_update_labbook_description(self, mock_create_labbooks, fixture_working_dir_env_repo_scoped):
        labbook_dir = os.path.join(mock_create_labbooks[1], 'default', 'default', 'labbooks', 'labbook1')
        assert os.path.exists(labbook_dir)

        desc_md = f"# Titłe\n ## \"Subtitle\"\n{'æbčdęfghį:*&^&%$%$@!_t ' * 200}. ## Ænother Sübtitle's\n{'xyz.?/<>č ' * 300}.\n"
        #desc_md = "abc"
        description_query = f"""
        mutation setDesc($content: String!) {{
            setLabbookDescription(input: {{
                owner: "default",
                labbookName: "labbook1",
                descriptionContent: $content
            }}) {{
                success
            }}
        }}
        """
        variables = {'content': desc_md}
        r = fixture_working_dir_env_repo_scoped[2].execute(description_query, variable_values=variables)
        assert 'errors' not in r
        assert r['data']['setLabbookDescription']['success'] is True

        # Get LabBook you just created
        query = """
        {
          labbook(name: "labbook1", owner: "default") {
            description
            isRepoClean
          }
        }
        """
        r = fixture_working_dir_env_repo_scoped[2].execute(query)
        assert 'errors' not in r
        # There's a lot of weird characters getting filtered out, make sure the bulk of the text remains
        assert abs(1.0 * len(r['data']['labbook']['description']) / len(desc_md)) > 0.75
        assert r['data']['labbook']['isRepoClean'] == True

    def test_delete_labbook_dry_run(self, mock_create_labbooks, fixture_working_dir_env_repo_scoped):
        """Test deleting a LabBook off disk. """
        labbook_dir = os.path.join(mock_create_labbooks[1], 'default', 'default', 'labbooks', 'labbook1')

        assert os.path.exists(labbook_dir)

        delete_query = f"""
        mutation delete {{
            deleteLabbook(input: {{
                owner: "default",
                labbookName: "labbook1",
                confirm: false
            }}) {{
                success
            }}
        }}
        """

        r = fixture_working_dir_env_repo_scoped[2].execute(delete_query)
        assert 'errors' not in r
        assert r['data']['deleteLabbook']['success'] is False
        assert os.path.exists(labbook_dir)

    def test_create_labbook_already_exists(self, fixture_working_dir_env_repo_scoped, snapshot):
        """Test listing labbooks"""
        query = """
        mutation myCreateLabbook($name: String!, $desc: String!, $repository: String!, 
                                 $base_id: String!, $revision: Int!) {
          createLabbook(input: {name: $name, description: $desc, 
                                repository: $repository, 
                                baseId: $base_id, revision: $revision}) {
            labbook {
              id
              name
              description
            }
          }
        }
        """
        variables = {"name": "test-lab-duplicate", "desc": "my test description",
                     "base_id": ENV_UNIT_TEST_BASE, "repository": ENV_UNIT_TEST_REPO,
                     "revision": ENV_UNIT_TEST_REV}
        snapshot.assert_match(fixture_working_dir_env_repo_scoped[2].execute(query, variable_values=variables))

        # Get LabBook you just created
        check_query = """
        {
          labbook(name: "test-lab-duplicate", owner: "default") {   
            name
            description
          }
        }
        """
        snapshot.assert_match(fixture_working_dir_env_repo_scoped[2].execute(check_query))

        # Second should fail with an error message
        snapshot.assert_match(fixture_working_dir_env_repo_scoped[2].execute(query, variable_values=variables))

    def test_move_file(self, mock_create_labbooks):
        """Test moving a file"""
        labbook_dir = os.path.join(mock_create_labbooks[1], 'default', 'default', 'labbooks', 'labbook1')
        os.makedirs(os.path.join(labbook_dir, 'code', 'subdir'))

        query = """
        mutation MoveLabbookFile {
            moveLabbookFile(
                input: {
                    owner: "default",
                    labbookName: "labbook1",
                    section: "code",
                    srcPath: "sillyfile",
                    dstPath: "subdir/sillyfile"
                }) {
                updatedEdges {
                    node {
                        id
                        key
                        isDir
                        size
                        section
                    }                    
                }
            }
        }
        """
        result_1 = mock_create_labbooks[2].execute(query)
        assert 'errors' not in result_1
        nodes = result_1['data']['moveLabbookFile']['updatedEdges']
        assert len(nodes) == 1
        assert nodes[0]['node']['key'] == 'subdir/sillyfile'
        assert nodes[0]['node']['isDir'] is False
        assert nodes[0]['node']['size'] == '7'
        assert nodes[0]['node']['section'] == 'code'

        os.makedirs(os.path.join(labbook_dir, 'code', 'subdir2'))
        query = """
        mutation MoveLabbookFile {
            moveLabbookFile(
                input: {
                owner: "default",
                labbookName: "labbook1",
                section: "code",
                srcPath: "subdir",
                dstPath: "subdir2"
            }) {
                updatedEdges {
                    node {
                        id
                        section
                        key
                        isDir
                        size
                    }                
                }
            }
        }
        """
        result_2 = mock_create_labbooks[2].execute(query)
        assert 'errors' not in result_2
        nodes = result_2['data']['moveLabbookFile']['updatedEdges']
        assert len(nodes) == 2
        assert nodes[0]['node']['key'] == 'subdir2/subdir/'
        assert nodes[0]['node']['isDir'] is True
        assert nodes[0]['node']['section'] == 'code'
        assert nodes[1]['node']['key'] == 'subdir2/subdir/sillyfile'
        assert nodes[1]['node']['isDir'] is False
        assert nodes[1]['node']['section'] == 'code'

        assert os.path.exists(os.path.join(labbook_dir, 'code', 'subdir2', 'subdir', 'sillyfile')) is True

    def test_move_file_many_times(self, mock_create_labbooks):
        """Test moving a file around a bunch"""
        labbook_dir = os.path.join(mock_create_labbooks[1], 'default', 'default', 'labbooks', 'labbook1', 'code')
        os.makedirs(os.path.join(labbook_dir, 'subdir'))

        query1 = """
        mutation MoveLabbookFile {
            moveLabbookFile(input: {
                owner: "default",
                labbookName: "labbook1",
                section: "code",
                srcPath: "sillyfile",
                dstPath: "subdir/sillyfile"
            }) {
                updatedEdges {
                    node {
                        section
                        key
                        isDir
                        size
                    }
            }
            }
        }
        """

        query2 = """
        mutation MoveLabbookFile {
            moveLabbookFile(input: {
                owner: "default",
                labbookName: "labbook1",
                section: "code",
                srcPath: "subdir/sillyfile",
                dstPath: "sillyfile"
            }) {
                updatedEdges {
                    node {
                        section
                        key
                        isDir
                        size
                    }
                }
            }
        }
        """
        result1 = mock_create_labbooks[2].execute(query1)
        assert 'errors' not in result1
        assert len(result1['data']['moveLabbookFile']['updatedEdges']) == 1
        assert result1['data']['moveLabbookFile']['updatedEdges'][0]['node']['key'] == 'subdir/sillyfile'
        assert result1['data']['moveLabbookFile']['updatedEdges'][0]['node']['isDir'] == False
        assert os.path.exists(os.path.join(labbook_dir, 'subdir', 'sillyfile'))
        assert os.path.isfile(os.path.join(labbook_dir, 'subdir', 'sillyfile'))

        result2 = mock_create_labbooks[2].execute(query2)
        assert 'errors' not in result2
        assert len(result2['data']['moveLabbookFile']['updatedEdges']) == 1
        assert result2['data']['moveLabbookFile']['updatedEdges'][0]['node']['key'] == 'sillyfile'
        assert result2['data']['moveLabbookFile']['updatedEdges'][0]['node']['isDir'] == False
        assert os.path.exists(os.path.join(labbook_dir, 'sillyfile'))
        assert os.path.isfile(os.path.join(labbook_dir, 'sillyfile'))

        result3 = mock_create_labbooks[2].execute(query1)
        assert 'errors' not in result3
        assert len(result3['data']['moveLabbookFile']['updatedEdges']) == 1
        assert result3['data']['moveLabbookFile']['updatedEdges'][0]['node']['key'] == 'subdir/sillyfile'
        assert result3['data']['moveLabbookFile']['updatedEdges'][0]['node']['isDir'] == False
        assert os.path.exists(os.path.join(labbook_dir, 'subdir', 'sillyfile'))
        assert os.path.isfile(os.path.join(labbook_dir, 'subdir', 'sillyfile'))

        result4 = mock_create_labbooks[2].execute(query2)
        assert len(result4['data']['moveLabbookFile']['updatedEdges']) == 1
        assert result4['data']['moveLabbookFile']['updatedEdges'][0]['node']['key'] == 'sillyfile'
        assert result4['data']['moveLabbookFile']['updatedEdges'][0]['node']['isDir'] == False
        assert os.path.exists(os.path.join(labbook_dir, 'sillyfile'))
        assert os.path.isfile(os.path.join(labbook_dir, 'sillyfile'))

        result5 = mock_create_labbooks[2].execute(query1)
        assert len(result5['data']['moveLabbookFile']['updatedEdges']) == 1
        assert result5['data']['moveLabbookFile']['updatedEdges'][0]['node']['key'] == 'subdir/sillyfile'
        assert result5['data']['moveLabbookFile']['updatedEdges'][0]['node']['isDir'] == False
        assert os.path.exists(os.path.join(labbook_dir, 'subdir', 'sillyfile'))
        assert os.path.isfile(os.path.join(labbook_dir, 'subdir', 'sillyfile'))

    def test_delete_file(self, mock_create_labbooks):
        query = """
        mutation deleteLabbookFiless {
          deleteLabbookFiles(
            input: {
              owner: "default",
              labbookName: "labbook1",
              section: "code",
              filePaths: ["sillyfile"]
            }) {
              success
            }
        }
        """
        filepath = os.path.join(mock_create_labbooks[1], 'default', 'default', 'labbooks', 'labbook1',
                                'code', 'sillyfile')
        assert os.path.exists(filepath) is True

        res = mock_create_labbooks[2].execute(query)
        assert res['data']['deleteLabbookFiles']['success'] is True

        assert os.path.exists(filepath) is False

    def test_delete_dir(self, mock_create_labbooks):
        im = InventoryManager(mock_create_labbooks[0])
        lb = im.load_labbook('default', 'default', 'labbook1')
        FileOperations.makedir(lb, 'code/subdir')

        test_file = os.path.join(lb.root_dir, 'code', 'subdir', 'test.txt')
        with open(test_file, 'wt') as tf:
            tf.write("puppers")

        lb.git.add_all('code/')
        lb.git.commit("blah")

        dir_path = os.path.join(lb.root_dir, 'code', 'subdir')
        assert os.path.exists(dir_path) is True
        assert os.path.exists(test_file) is True

        # Note, deleting a file should work with and without a trailing / at the end.
        query = """
        mutation deleteLabbookFiles {
          deleteLabbookFiles(
            input: {
              owner: "default",
              labbookName: "labbook1",
              section: "code",
              filePaths: ["subdir/"]
            }) {
              success
            }
        }
        """
        res = mock_create_labbooks[2].execute(query)
        print(res)
        assert res['data']['deleteLabbookFiles']['success'] is True

        assert os.path.exists(dir_path) is False
        assert os.path.exists(test_file) is False
        assert os.path.exists(os.path.join(lb.root_dir, 'code')) is True

    def test_makedir(self, mock_create_labbooks, snapshot):
        query = """
        mutation makeLabbookDirectory {
          makeLabbookDirectory(
            input: {
              owner: "default",
              labbookName: "labbook1",
              section: "output",
              directory: "new_folder",
            }) {
              newLabbookFileEdge {
                node{
                  key
                  isDir
                  size
                }
              }
            }}"""
        snapshot.assert_match(mock_create_labbooks[2].execute(query))

    def test_write_readme(self, mock_create_labbooks, snapshot):
        flush_redis_repo_cache()
        content = json.dumps('##Overview\n\nThis is my readme\n :df,a//3p49kasdf')

        query = f"""
        mutation writeReadme {{
          writeLabbookReadme(
            input: {{
              owner: "default",
              labbookName: "labbook1",
              content: {content},
            }}) {{
              updatedLabbook{{
                name
                description
                overview{{
                    readme
                }}
              }}
            }}
        }}
        """
        snapshot.assert_match(mock_create_labbooks[2].execute(query))

    def test_fetch_labbook_edge(self, mock_create_labbooks):
        query = f"""
        mutation f {{
            fetchLabbookEdge(input:{{
                owner: "default",
                labbookName: "labbook1"
            }}) {{
                newLabbookEdge {{
                    node {{
                        name
                        owner
                    }}
                }}
            }}
        }}
        """
        r = mock_create_labbooks[2].execute(query)
        assert 'errors' not in r
        assert r['data']['fetchLabbookEdge']['newLabbookEdge']['node']['owner'] == 'default'
        assert r['data']['fetchLabbookEdge']['newLabbookEdge']['node']['name'] == 'labbook1'

