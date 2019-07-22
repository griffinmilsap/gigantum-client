import os
import io
import tempfile
import pprint
import math
import hashlib

import pytest
from werkzeug.datastructures import FileStorage
from graphene.test import Client

from gtmcore.configuration.utils import call_subprocess
from gtmcore.inventory.inventory import InventoryManager
from gtmcore.labbook import SecretStore

from lmsrvcore.middleware import DataloaderMiddleware
from lmsrvlabbook.tests.fixtures import (fixture_working_dir_env_repo_scoped, fixture_working_dir)


@pytest.fixture()
def mock_config():
    pass


@pytest.fixture()
def mock_upload_key():
    with tempfile.TemporaryDirectory() as tempdir:
        # Make an approx 10MB key file, in order to test file uploadings
        # in multiple "chunks"
        with open(os.path.join(tempdir, 'id_rsa'), 'w') as f:
            f.write(f'---BEGIN---\n{"12345ABCDE" * 1000000}\n---END---\n')
        yield f


class TestSecretsQueries:
    def test_secrets_vault_query(self, fixture_working_dir_env_repo_scoped):
        client = fixture_working_dir_env_repo_scoped[2]
        im = InventoryManager(fixture_working_dir_env_repo_scoped[0])
        lb = im.create_labbook("default", "default", "unittest-create-secret")
        sec_store = SecretStore(lb, "default")
        container_dst = '/tmp/secrets1'

        sec_store['data1.key'] = container_dst
        sec_store['absent.key'] = container_dst

        with tempfile.TemporaryDirectory() as tdir:
            path = os.path.join(tdir, 'data1.key')
            f1 = open(path, 'w')
            f1.write('<<<keydata>>>')
            f1.close()
            sec_store.insert_file(f1.name)

        query = """
        {
            labbook(owner: "default", name: "unittest-create-secret") {
                environment {
                    secretsFileMapping {
                        edges {
                            node {
                                filename
                                mountPath
                                isPresent
                            }
                        }
                    }
                }
            }
        }
        """
        r = client.execute(query)
        pprint.pprint(r)
        assert 'errors' not in r

        # Test that an absent file (whose contents should be uploaded) is acknowledged, but returns
        # False for isPresent
        assert r['data']['labbook']['environment']['secretsFileMapping']['edges'][0]['node']['filename'] == 'absent.key'
        assert r['data']['labbook']['environment']['secretsFileMapping']['edges'][0]['node']['isPresent'] == False
        assert r['data']['labbook']['environment']['secretsFileMapping']['edges'][0]['node']['mountPath'] == container_dst

        # This file is in the registry AND isPresent
        assert r['data']['labbook']['environment']['secretsFileMapping']['edges'][1]['node']['filename'] == 'data1.key'
        assert r['data']['labbook']['environment']['secretsFileMapping']['edges'][1]['node']['isPresent'] == True
        assert r['data']['labbook']['environment']['secretsFileMapping']['edges'][1]['node']['mountPath'] == container_dst


class TestSecretsMutations:
    def test_insert_secrets_entry(self, fixture_working_dir_env_repo_scoped):
        client = fixture_working_dir_env_repo_scoped[2]
        im = InventoryManager(fixture_working_dir_env_repo_scoped[0])
        lb = im.create_labbook("default", "default", "unittest-mutation-create-secret")
        query = """
        mutation insert {
            insertSecretsEntry(input: {
                owner: "default",
                labbookName: "unittest-mutation-create-secret",
                filename: "example.key",
                mountPath: "/opt/path"
            }) {
                environment {
                    secretsFileMapping {
                        edges {
                            node {
                                filename
                                mountPath
                                isPresent
                            }
                        }
                    }
                }
            }
        }"""
        r = client.execute(query)
        assert 'errors' not in r
        n = r['data']['insertSecretsEntry']['environment']['secretsFileMapping']['edges'][0]['node']
        assert n['filename'] == 'example.key'
        assert n['isPresent'] == False
        assert n['mountPath'] == '/opt/path'

        # Check that secrets.json is tracked.
        secstore = SecretStore(lb, "default")
        p = call_subprocess(f"git ls-files {secstore.secret_path}".split(), cwd=lb.root_dir)
        assert p.strip() == '.gigantum/secrets.json'
        assert 'Created entry for secrets file' in lb.git.log()[0]['message']

    def test_remove_secrets_entry(self, fixture_working_dir_env_repo_scoped):
        client = fixture_working_dir_env_repo_scoped[2]
        im = InventoryManager(fixture_working_dir_env_repo_scoped[0])
        lb = im.create_labbook("default", "default", "unittest-mutation-remove-secret")
        SecretStore(lb, "default")['remove.key'] = '/mnt/nowhere'
        SecretStore(lb, "default")['absent.key'] = '/mnt/nowhere2'
        query = """
        mutation remove {
            removeSecretsEntry(input: {
                owner: "default",
                labbookName: "unittest-mutation-remove-secret",
                filename: "remove.key",
            }) {
                environment {
                    secretsFileMapping {
                        edges {
                            node {
                                filename
                                mountPath
                                isPresent
                            }
                        }
                    }
                }
            }
        }"""
        r = client.execute(query)
        assert 'errors' not in r
        n = r['data']['removeSecretsEntry']['environment']['secretsFileMapping']['edges']
        assert len(n) == 1
        assert n[0]['node']['filename'] == 'absent.key'
        assert n[0]['node']['isPresent'] == False

    def test_upload_secrets_file(self, fixture_working_dir, mock_upload_key):

        class DummyContext(object):
            def __init__(self, file_handle):
                self.labbook_loader = None
                self.files = {'uploadChunk': file_handle}

        client = Client(fixture_working_dir[3], middleware=[DataloaderMiddleware()])

        im = InventoryManager(fixture_working_dir[0])
        lb = im.create_labbook("default", "default", "unittest-upload-secret")
        secret_store = SecretStore(lb, "default")
        secret_store['id_rsa'] = '/opt/secrets/location/in/container'
        initial_hash = hashlib.md5(open(mock_upload_key.name, 'rb').read()).hexdigest()

        new_file_size = os.path.getsize(mock_upload_key.name)
        chunk_size = 4194000
        file_info = os.stat(mock_upload_key.name)
        file_size = int(file_info.st_size / 1000)
        total_chunks = int(math.ceil(file_info.st_size / chunk_size))

        mf = open(mock_upload_key.name)
        for chunk_index in range(total_chunks):
            chunk = io.BytesIO()
            chunk.write(mf.read(chunk_size).encode())
            chunk.seek(0)
            upload_query = f"""
            mutation upload {{
                uploadSecretsFile(input: {{
                    owner: "default",
                    labbookName: "unittest-upload-secret",
                    transactionId: "unittest-txid-9999",
                    chunkUploadParams: {{
                        uploadId: "rando-upload-id-1234",
                        chunkSize: {chunk_size},
                        totalChunks: {total_chunks},
                        chunkIndex: {chunk_index},
                        fileSize: "{file_size}",
                        filename: "{os.path.basename(mock_upload_key.name)}"
                    }}
                }}) {{
                    environment {{
                        secretsFileMapping {{
                            edges {{
                                node {{
                                    filename
                                    isPresent
                                    mountPath
                                }}
                            }}
                        }}
                    }}
                }}
            }}"""

            file = FileStorage(chunk)
            r = client.execute(upload_query, context_value=DummyContext(file))

        secret_info = r['data']['uploadSecretsFile']['environment']['secretsFileMapping']['edges'][0]['node']
        assert secret_info['filename'] == 'id_rsa'
        assert secret_info['mountPath'] == '/opt/secrets/location/in/container'
        assert secret_info['isPresent'] is True

        # Test that the uploaded file hash exactly matches that as the one in the "vault"
        d = secret_store.as_mount_dict
        uploaded_hash = hashlib.md5(open(f'{list(d.keys())[0]}', 'rb').read()).hexdigest()
        assert initial_hash == uploaded_hash

    def test_delete_secrets_file(self, fixture_working_dir_env_repo_scoped):
        client = fixture_working_dir_env_repo_scoped[2]
        im = InventoryManager(fixture_working_dir_env_repo_scoped[0])
        lb = im.create_labbook("default", "default", "unittest-mutation-delete-secret")
        secstore = SecretStore(lb, "default")
        secstore['remove.key'] = '/mnt/nowhere'
        secstore['absent.key'] = '/mnt/nowhere2'

        with tempfile.TemporaryDirectory() as tdir:
            path = os.path.join(tdir, 'remove.key')
            f1 = open(path, 'w')
            f1.write('<<<keydata>>>')
            f1.close()
            secstore.insert_file(f1.name)

        query = """
        mutation delete {
            deleteSecretsFile(input: {
                owner: "default",
                labbookName: "unittest-mutation-delete-secret",
                filename: "remove.key",
            }) {
                environment {
                    secretsFileMapping {
                        edges {
                            node {
                                filename
                                mountPath
                                isPresent
                            }
                        }
                    }
                }
            }
        }"""
        r = client.execute(query)
        assert 'errors' not in r
        n = r['data']['deleteSecretsFile']['environment']['secretsFileMapping']['edges']
        assert n[0]['node']['filename'] == 'absent.key'
        assert n[0]['node']['isPresent'] is False
        assert n[0]['node']['mountPath'] == '/mnt/nowhere2'

        assert n[1]['node']['filename'] == 'remove.key'
        assert n[1]['node']['isPresent'] is False
        assert n[1]['node']['mountPath'] == '/mnt/nowhere'

