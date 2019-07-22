import pytest
import os
import tempfile
import io
import math

from lmsrvlabbook.tests.fixtures import fixture_working_dir_env_repo_scoped, fixture_working_dir

from graphene.test import Client
from werkzeug.datastructures import FileStorage

from gtmcore.dispatcher.jobs import export_dataset_as_zip
from gtmcore.files import FileOperations

from gtmcore.inventory.inventory import InventoryManager

from lmsrvcore.middleware import DataloaderMiddleware

from gtmcore.fixtures.datasets import mock_dataset_with_cache_dir, mock_dataset_with_manifest, helper_append_file

from gtmcore.fixtures import _MOCK_create_remote_repo2


class TestDatasetSharingMutations(object):
    def test_import_dataset(self, fixture_working_dir):
        """Test batch uploading, but not full import"""
        class DummyContext(object):
            def __init__(self, file_handle):
                self.dataset_loader = None
                self.files = {'uploadChunk': file_handle}

        client = Client(fixture_working_dir[3], middleware=[DataloaderMiddleware()])

        # Create a temporary dataset
        ds = InventoryManager(fixture_working_dir[0]).create_dataset("default", "default", "test-export",
                                                                     "gigantum_object_v1",
                                                                     description="Tester")

        # Create a largeish file in the dir
        with open(os.path.join(fixture_working_dir[1], 'testfile.bin'), 'wb') as testfile:
            testfile.write(os.urandom(9000000))
        FileOperations.insert_file(ds, 'input', testfile.name)

        # Export dataset
        zip_file = export_dataset_as_zip(ds.root_dir, tempfile.gettempdir())
        ds_dir = ds.root_dir

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
                              importDataset(input:{{
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
                    assert type(result['data']['importDataset']['importJobKey']) == str
                    assert "rq:job:" in result['data']['importDataset']['importJobKey']

                chunk.close()

    def test_export_dataset(self, fixture_working_dir):
        """Test export"""
        create_query = """
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
        create_variables = {"name": "test-dataset-1", "desc": "my test dataset",
                            "storage_type": "gigantum_object_v1"}

        fixture_working_dir[2].execute(create_query, variable_values=create_variables)

        query = """
                mutation myMutation($owner: String!, $datasetName: String!) {
                  exportDataset(input: {owner: $owner, datasetName: $datasetName}) {
                      jobKey
                  }
                }
                """
        variables = {"datasetName": "test-dataset-1", "owner": "default"}
        result = fixture_working_dir[2].execute(query, variable_values=variables)
        assert "errors" not in result
        assert type(result['data']['exportDataset']['jobKey']) == str
        assert "rq:job:" in result['data']['exportDataset']['jobKey']
