import os
import io
import math
import tempfile
import time
from mock import patch
import pytest
import json
from graphene.test import Client
from werkzeug.datastructures import FileStorage

import gtmcore.dispatcher.dataset_jobs
from gtmcore.inventory.inventory import InventoryManager
from gtmcore.dataset.cache.filesystem import HostFilesystemCache
from gtmcore.dataset.manifest import Manifest
from lmsrvcore.middleware import DataloaderMiddleware
from lmsrvlabbook.tests.fixtures import fixture_working_dir
from gtmcore.dispatcher import Dispatcher, jobs


@pytest.fixture()
def mock_create_dataset(fixture_working_dir):
    # Create a dataset in the temporary directory
    im = InventoryManager(fixture_working_dir[0])
    ds = im.create_dataset("default", "default", "dataset1", storage_type="gigantum_object_v1",
                           description="my dataset")

    # name of the config file, temporary working directory, the schema
    yield fixture_working_dir


class TestDatasetUploadFilesMutations(object):
    def test_add_file(self, mock_create_dataset):
        """Test adding a new file to a dataset"""

        class DummyContext(object):
            def __init__(self, file_handle):
                self.dataset_loader = None
                self.labbook_loader = None
                self.files = {'uploadChunk': file_handle}

        def dispatcher_mock(self, function_ref, kwargs, metadata):
            assert kwargs['logged_in_username'] == 'default'
            assert kwargs['logged_in_email'] == 'jane@doe.com'
            assert kwargs['dataset_owner'] == 'default'
            assert kwargs['dataset_name'] == 'dataset1'

            # Inject mocked config file
            kwargs['config_file'] = mock_create_dataset[0]

            # Stop patching so job gets scheduled for real
            dispatcher_patch.stop()

            # Call same method as in mutation
            d = Dispatcher()
            kwargs['dispatcher'] = Dispatcher
            res = d.dispatch_task(gtmcore.dispatcher.dataset_jobs.complete_dataset_upload_transaction,
                                  kwargs=kwargs, metadata=metadata)

            return res

        client = Client(mock_create_dataset[3], middleware=[DataloaderMiddleware()])

        # Create file to upload
        test_file = os.path.join(tempfile.gettempdir(), "myValidFile.dat")
        est_size = 9000000
        try:
            os.remove(test_file)
        except:
            pass
        with open(test_file, 'wb') as tf:
            tf.write(os.urandom(est_size))

        new_file_size = os.path.getsize(tf.name)
        # Get upload params
        chunk_size = 4194000
        file_info = os.stat(test_file)
        file_size = int(file_info.st_size / 1000)
        total_chunks = int(math.ceil(file_info.st_size / chunk_size))

        ds = InventoryManager(mock_create_dataset[0]).load_dataset('default', 'default', 'dataset1')

        fsc = HostFilesystemCache(ds, 'default')
        target_file = os.path.join(fsc.current_revision_dir, "myValidFile.dat")

        txid = "000-unitest-transaction"
        with open(test_file, 'rb') as tf:
            # Check for file to exist (shouldn't yet)
            assert os.path.exists(target_file) is False
            for chunk_index in range(total_chunks):
                # Upload a chunk
                chunk = io.BytesIO()
                chunk.write(tf.read(chunk_size))
                chunk.seek(0)
                file = FileStorage(chunk)

                query = f"""
                            mutation addDatasetFile{{
                              addDatasetFile(input:{{owner:"default",
                                                      datasetName: "dataset1",
                                                      filePath: "myValidFile.dat",
                                                      transactionId: "{txid}",
                                chunkUploadParams:{{
                                  uploadId: "fdsfdsfdsfdfs",
                                  chunkSize: {chunk_size},
                                  totalChunks: {total_chunks},
                                  chunkIndex: {chunk_index},
                                  fileSize: "{file_size}",
                                  filename: "{os.path.basename(test_file)}"
                                }}
                              }}) {{
                                      newDatasetFileEdge {{
                                        node{{
                                          id
                                          key
                                          isDir
                                          size
                                        }}
                                      }}
                                    }}
                            }}
                            """
                r = client.execute(query, context_value=DummyContext(file))
                assert 'errors' not in r

        # So, these will only be populated once the last chunk is uploaded. Will be None otherwise.
        assert r['data']['addDatasetFile']['newDatasetFileEdge']['node']['isDir'] is False
        assert r['data']['addDatasetFile']['newDatasetFileEdge']['node']['key'] == 'myValidFile.dat'
        assert r['data']['addDatasetFile']['newDatasetFileEdge']['node']['size'] == f"{new_file_size}"
        # When done uploading, file should exist in the labbook
        assert os.path.exists(target_file)
        assert os.path.isfile(target_file)

        complete_query = f"""
        mutation completeQuery {{
            completeDatasetUploadTransaction(input: {{
                owner: "default",
                datasetName: "dataset1",
                transactionId: "{txid}"
            }}) {{
                backgroundJobKey
            }}
        }}
        """

        # Patch dispatch_task so you can inject the mocked config file
        dispatcher_patch = patch.object(Dispatcher, 'dispatch_task', dispatcher_mock)
        dispatcher_patch.start()

        r = client.execute(complete_query, context_value=DummyContext(None))
        assert 'errors' not in r

        job_query = f"""
                       {{
                           jobStatus(jobId: "{r['data']['completeDatasetUploadTransaction']['backgroundJobKey']}")
                            {{                                
                                status
                                result
                                status
                                jobMetadata
                                failureMessage
                                startedAt
                                finishedAt
                            }}
                       }}
                       """

        cnt = 0
        while cnt < 20:
            job_result = client.execute(job_query, context_value=DummyContext(None))
            assert 'errors' not in job_result
            if job_result['data']['jobStatus']['status'] == 'finished':
                break
            time.sleep(.25)

        assert cnt < 20
        metadata = json.loads(job_result['data']['jobStatus']['jobMetadata'])
        assert metadata['percent_complete'] == 100
        assert metadata['feedback'] == 'Please wait while file contents are analyzed. 9 MB of 9 MB complete...'

        # Verify file was added and repo is clean
        m = Manifest(ds, 'default')
        status = m.status()
        assert len(status.created) == 0
        assert len(status.modified) == 0
        assert len(status.deleted) == 0

        assert 'Uploaded 1 new file(s)' in ds.git.log()[0]['message']

    def test_add_file_errors(self, mock_create_dataset, snapshot):
        """Test new file error handling"""

        class DummyContext(object):
            def __init__(self, file_handle):
                self.labbook_loader = None
                self.files = {'blah': file_handle}

        client = Client(mock_create_dataset[3])

        query = f"""
                    mutation addDatasetFile{{
                      addDatasetFile(input:{{owner:"default",
                                              datasetName: "dataset1",
                                              filePath: "myValidFile.dat",
                                              transactionId: "adsfasdfasdf",
                        chunkUploadParams:{{
                          uploadId: "fdsfdsfdsfdfs",
                          chunkSize: 200,
                          totalChunks: 2,
                          chunkIndex: 0,
                          fileSize: "6777",
                          filename: "asdfh"
                        }}
                      }}) {{
                              newDatasetFileEdge {{
                                node{{
                                  id
                                  key
                                  isDir
                                  size
                                }}
                              }}
                            }}
                    }}
                    """
        # Fail because no file
        r = client.execute(query, context_value=DummyContext(None))
        assert 'errors' in r
