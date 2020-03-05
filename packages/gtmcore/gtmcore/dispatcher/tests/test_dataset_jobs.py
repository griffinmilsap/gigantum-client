import os
import pytest
import time

import uuid
from aioresponses import aioresponses
import snappy
from mock import patch
from collections import namedtuple
import responses

import gtmcore
import gtmcore.dispatcher.dataset_jobs
from gtmcore.configuration import Configuration
from gtmcore.dataset.io.manager import IOManager
from gtmcore.dataset.manifest import Manifest
from gtmcore.dispatcher import jobs

from gtmcore.dataset.tests.test_storage_local import mock_dataset_with_local_dir
from gtmcore.fixtures import mock_config_file, mock_config_file_background_tests, _MOCK_create_remote_repo2
from gtmcore.fixtures.datasets import helper_append_file, helper_compress_file, helper_write_big_file, \
    mock_enable_unmanaged_for_testing, mock_dataset_with_cache_dir_local


from gtmcore.inventory.inventory import InventoryManager, InventoryException
from gtmcore.dispatcher.dispatcher import Dispatcher
from gtmcore.dispatcher.tests import BG_SKIP_MSG, BG_SKIP_TEST


@pytest.fixture()
def mock_dataset_head():
    """A pytest fixture that creates a dataset in a temp working dir. Deletes directory after test"""
    with responses.RequestsMock() as rsps:
        rsps.add(responses.HEAD, 'https://api.gigantum.com/object-v1/default/dataset100',
                 headers={'x-access-level': 'a'}, status=200)
        yield


@pytest.mark.skipif(BG_SKIP_TEST, reason=BG_SKIP_MSG)
class TestDatasetBackgroundJobs(object):
    def test_pull_objects(self, mock_config_file, mock_dataset_head):
        im = InventoryManager(mock_config_file[0])
        ds = im.create_dataset('default', 'default', "dataset100", storage_type="gigantum_object_v1", description="100")
        m = Manifest(ds, 'default')
        iom = IOManager(ds, m)

        os.makedirs(os.path.join(m.cache_mgr.cache_root, m.dataset_revision, "other_dir"))
        helper_append_file(m.cache_mgr.cache_root, m.dataset_revision, "test1.txt", "asdfadfsdf")
        helper_append_file(m.cache_mgr.cache_root, m.dataset_revision, "test2.txt", "fdsfgfd")
        m.sweep_all_changes()

        obj_to_push = iom.objects_to_push()
        assert len(obj_to_push) == 2
        _, obj_id_1 = obj_to_push[0].object_path.rsplit('/', 1)
        _, obj_id_2 = obj_to_push[1].object_path.rsplit('/', 1)
        obj1_target = obj_to_push[0].object_path
        obj2_target = obj_to_push[1].object_path

        obj1_source = os.path.join('/tmp', uuid.uuid4().hex)
        obj2_source = os.path.join('/tmp', uuid.uuid4().hex)

        assert os.path.exists(obj1_target) is True
        assert os.path.exists(obj2_target) is True
        helper_compress_file(obj1_target, obj1_source)
        helper_compress_file(obj2_target, obj2_source)
        assert os.path.isfile(obj1_target) is False
        assert os.path.isfile(obj2_target) is False
        assert os.path.isfile(obj1_source) is True
        assert os.path.isfile(obj2_source) is True

        # Clear out from linked dir
        os.remove(os.path.join(m.cache_mgr.cache_root, m.dataset_revision, 'test1.txt'))
        os.remove(os.path.join(m.cache_mgr.cache_root, m.dataset_revision, 'test2.txt'))

        with patch.object(Configuration, 'find_default_config', lambda self: mock_config_file[0]):
            with aioresponses() as mocked_responses:
                mocked_responses.get(f'https://api.gigantum.com/object-v1/{ds.namespace}/{ds.name}/{obj_id_1}',
                                     payload={
                                             "presigned_url": f"https://dummyurl.com/{obj_id_1}?params=1",
                                             "namespace": ds.namespace,
                                             "obj_id": obj_id_1,
                                             "dataset": ds.name
                                     },
                                     status=200)

                with open(obj1_source, 'rb') as data1:
                    mocked_responses.get(f"https://dummyurl.com/{obj_id_1}?params=1",
                                         body=data1.read(), status=200,
                                         content_type='application/octet-stream')

                mocked_responses.get(f'https://api.gigantum.com/object-v1/{ds.namespace}/{ds.name}/{obj_id_2}',
                                     payload={
                                             "presigned_url": f"https://dummyurl.com/{obj_id_2}?params=1",
                                             "namespace": ds.namespace,
                                             "obj_id": obj_id_2,
                                             "dataset": ds.name
                                     },
                                     status=200)

                with open(obj2_source, 'rb') as data2:
                    mocked_responses.get(f"https://dummyurl.com/{obj_id_2}?params=1",
                                         body=data2.read(), status=200,
                                         content_type='application/octet-stream')

                dl_kwargs = {
                    'logged_in_username': "default",
                    'access_token': "asdf",
                    'id_token': "1234",
                    'dataset_owner': "default",
                    'dataset_name': "dataset100",
                    'labbook_owner': None,
                    'labbook_name': None,
                    'keys': ["test1.txt"]
                }

                gtmcore.dispatcher.dataset_jobs.pull_objects(**dl_kwargs)

                # Manually link since this is disabled by default in the job (because in real use, multiple jobs run
                # in parallel and you only want to link once.
                m.link_revision()

                assert os.path.isfile(obj1_target) is True
                assert os.path.isfile(obj2_target) is False

                decompressor = snappy.StreamDecompressor()
                with open(obj1_source, 'rb') as dd:
                    source1 = decompressor.decompress(dd.read())
                    source1 += decompressor.flush()
                with open(obj1_target, 'rt') as dd:
                    dest1 = dd.read()
                assert source1.decode("utf-8") == dest1

                # Download other file
                dl_kwargs = {
                    'logged_in_username': "default",
                    'access_token': "asdf",
                    'id_token': "1234",
                    'dataset_owner': "default",
                    'dataset_name': "dataset100",
                    'labbook_owner': None,
                    'labbook_name': None,
                    'keys': ["test2.txt"]
                }

                gtmcore.dispatcher.dataset_jobs.pull_objects(**dl_kwargs)

                # Manually link since this is disabled by default in the job (because in real use, multiple jobs run
                # in parallel and you only want to link once.
                m.link_revision()

                assert os.path.isfile(obj1_target) is True
                assert os.path.isfile(obj2_target) is True

                with open(obj1_source, 'rb') as dd:
                    source1 = decompressor.decompress(dd.read())
                    source1 += decompressor.flush()
                with open(obj1_target, 'rt') as dd:
                    dest1 = dd.read()
                assert source1.decode("utf-8") == dest1

                with open(obj2_source, 'rb') as dd:
                    source1 = decompressor.decompress(dd.read())
                    source1 += decompressor.flush()
                with open(obj2_target, 'rt') as dd:
                    dest1 = dd.read()
                assert source1.decode("utf-8") == dest1

    def test_pull_objects_error(self, mock_config_file, mock_dataset_head):
        im = InventoryManager(mock_config_file[0])
        ds = im.create_dataset('default', 'default', "dataset100", storage_type="gigantum_object_v1", description="100")
        m = Manifest(ds, 'default')
        iom = IOManager(ds, m)

        os.makedirs(os.path.join(m.cache_mgr.cache_root, m.dataset_revision, "other_dir"))
        helper_append_file(m.cache_mgr.cache_root, m.dataset_revision, "test1.txt", "asdfadfsdf")
        helper_append_file(m.cache_mgr.cache_root, m.dataset_revision, "test2.txt", "fdsfgfd")
        m.sweep_all_changes()

        obj_to_push = iom.objects_to_push()
        assert len(obj_to_push) == 2
        _, obj_id_1 = obj_to_push[0].object_path.rsplit('/', 1)
        _, obj_id_2 = obj_to_push[1].object_path.rsplit('/', 1)
        obj1_target = obj_to_push[0].object_path
        obj2_target = obj_to_push[1].object_path

        obj1_source = os.path.join('/tmp', uuid.uuid4().hex)
        obj2_source = os.path.join('/tmp', uuid.uuid4().hex)

        assert os.path.exists(obj1_target) is True
        assert os.path.exists(obj2_target) is True
        helper_compress_file(obj1_target, obj1_source)
        helper_compress_file(obj2_target, obj2_source)
        assert os.path.isfile(obj1_target) is False
        assert os.path.isfile(obj2_target) is False
        assert os.path.isfile(obj1_source) is True
        assert os.path.isfile(obj2_source) is True

        # Clear out from linked dir
        os.remove(os.path.join(m.cache_mgr.cache_root, m.dataset_revision, 'test1.txt'))
        os.remove(os.path.join(m.cache_mgr.cache_root, m.dataset_revision, 'test2.txt'))

        with patch.object(Configuration, 'find_default_config', lambda self: mock_config_file[0]):
            with aioresponses() as mocked_responses:
                mocked_responses.get(f'https://api.gigantum.com/object-v1/{ds.namespace}/{ds.name}/{obj_id_1}',
                                     payload={
                                             "presigned_url": f"https://dummyurl.com/{obj_id_1}?params=1",
                                             "namespace": ds.namespace,
                                             "obj_id": obj_id_1,
                                             "dataset": ds.name
                                     },
                                     status=200)

                with open(obj1_source, 'rb') as data1:
                    mocked_responses.get(f"https://dummyurl.com/{obj_id_1}?params=1",
                                         body=data1.read(), status=200,
                                         content_type='application/octet-stream')

                mocked_responses.get(f'https://api.gigantum.com/object-v1/{ds.namespace}/{ds.name}/{obj_id_2}',
                                     payload={
                                             "presigned_url": f"https://dummyurl.com/{obj_id_2}?params=1",
                                             "namespace": ds.namespace,
                                             "obj_id": obj_id_2,
                                             "dataset": ds.name
                                     },
                                     status=400)

                dl_kwargs = {
                    'logged_in_username': "default",
                    'access_token': "asdf",
                    'id_token': "1234",
                    'dataset_owner': "default",
                    'dataset_name': "dataset100",
                    'labbook_owner': None,
                    'labbook_name': None,
                    'keys': ['test1.txt', 'test2.txt']
                }

                gtmcore.dispatcher.dataset_jobs.pull_objects(**dl_kwargs)

                # Manually link since this is disabled by default in the job (because in real use, multiple jobs run
                # in parallel and you only want to link once.
                m.link_revision()

                assert os.path.isfile(obj1_target) is True
                assert os.path.isfile(obj2_target) is False
                assert os.path.isfile(os.path.join(m.cache_mgr.cache_root, m.dataset_revision, 'test1.txt')) is True
                assert os.path.isfile(os.path.join(m.cache_mgr.cache_root, m.dataset_revision, 'test2.txt')) is False

    def test_update_from_remote(self, mock_dataset_with_local_dir):
        ds = mock_dataset_with_local_dir[0]
        m = Manifest(ds, 'tester')

        assert len(m.manifest.keys()) == 0

        kwargs = {
            'logged_in_username': "tester",
            'access_token': "asdf",
            'id_token': "1234",
            'dataset_owner': "tester",
            'dataset_name': 'dataset-1'
        }

        jobs.update_unmanaged_dataset_from_remote(**kwargs)

        m = Manifest(ds, 'tester')
        assert len(m.manifest.keys()) == 4
        assert os.path.isfile(os.path.join(m.cache_mgr.cache_root, m.dataset_revision, 'test1.txt'))
        assert os.path.isfile(os.path.join(m.cache_mgr.cache_root, m.dataset_revision, 'test2.txt'))
        assert os.path.isfile(os.path.join(m.cache_mgr.cache_root, m.dataset_revision, 'subdir', 'test3.txt'))

    def test_update_from_local(self, mock_dataset_with_local_dir):
        ds = mock_dataset_with_local_dir[0]
        m = Manifest(ds, 'tester')
        assert len(m.manifest.keys()) == 0

        ds.backend.update_from_remote(ds, lambda x: print(x))

        m = Manifest(ds, 'tester')
        assert len(m.manifest.keys()) == 4
        assert os.path.isfile(os.path.join(m.cache_mgr.cache_root, m.dataset_revision, 'test1.txt'))
        assert os.path.isfile(os.path.join(m.cache_mgr.cache_root, m.dataset_revision, 'test2.txt'))
        assert os.path.isfile(os.path.join(m.cache_mgr.cache_root, m.dataset_revision, 'subdir', 'test3.txt'))

        modified_items = ds.backend.verify_contents(ds, lambda x: print(x))
        assert len(modified_items) == 0

        test_dir = os.path.join(mock_dataset_with_local_dir[1], "local_data", "test_dir")
        with open(os.path.join(test_dir, 'test1.txt'), 'wt') as tf:
            tf.write("This file got changed in the filesystem")

        modified_items = ds.backend.verify_contents(ds, lambda x: print(x))
        assert len(modified_items) == 1
        assert 'test1.txt' in modified_items

        kwargs = {
            'logged_in_username': "tester",
            'access_token': "asdf",
            'id_token': "1234",
            'dataset_owner': "tester",
            'dataset_name': 'dataset-1'
        }

        jobs.update_unmanaged_dataset_from_local(**kwargs)

        assert len(m.manifest.keys()) == 4
        assert os.path.isfile(os.path.join(m.cache_mgr.cache_root, m.dataset_revision, 'test1.txt'))
        assert os.path.isfile(os.path.join(m.cache_mgr.cache_root, m.dataset_revision, 'test2.txt'))
        assert os.path.isfile(os.path.join(m.cache_mgr.cache_root, m.dataset_revision, 'subdir', 'test3.txt'))

        modified_items = ds.backend.verify_contents(ds, lambda x: print(x))
        assert len(modified_items) == 0

        with open(os.path.join(m.cache_mgr.cache_root, m.dataset_revision, 'test1.txt'), 'rt') as tf:
            assert tf.read() == "This file got changed in the filesystem"

    def test_verify_contents(self, mock_dataset_with_local_dir):
        class JobMock():
            def __init__(self):
                self.meta = dict()
            def save_meta(self):
                pass

        CURRENT_JOB = JobMock()

        def get_current_job_mock():
            return CURRENT_JOB

        with patch('gtmcore.dispatcher.jobs.get_current_job', side_effect=get_current_job_mock):
            ds = mock_dataset_with_local_dir[0]
            m = Manifest(ds, 'tester')
            assert len(m.manifest.keys()) == 0

            ds.backend.update_from_remote(ds, lambda x: print(x))

            m = Manifest(ds, 'tester')
            assert len(m.manifest.keys()) == 4
            assert os.path.isfile(os.path.join(m.cache_mgr.cache_root, m.dataset_revision, 'test1.txt'))
            assert os.path.isfile(os.path.join(m.cache_mgr.cache_root, m.dataset_revision, 'test2.txt'))
            assert os.path.isfile(os.path.join(m.cache_mgr.cache_root, m.dataset_revision, 'subdir', 'test3.txt'))

            modified_items = ds.backend.verify_contents(ds, lambda x: print(x))
            assert len(modified_items) == 0

            test_dir = os.path.join(mock_dataset_with_local_dir[1], "local_data", "test_dir")
            with open(os.path.join(test_dir, 'test1.txt'), 'wt') as tf:
                tf.write("This file got changed in the filesystem")

            modified_items = ds.backend.verify_contents(ds, lambda x: print(x))
            assert len(modified_items) == 1
            assert 'test1.txt' in modified_items

            kwargs = {
                'logged_in_username': "tester",
                'access_token': "asdf",
                'id_token': "1234",
                'dataset_owner': "tester",
                'dataset_name': 'dataset-1'
            }

            jobs.verify_dataset_contents(**kwargs)
            job = gtmcore.dispatcher.jobs.get_current_job()

            assert 'modified_keys' in job.meta
            assert job.meta['modified_keys'] == ["test1.txt"]
            assert 'Validating contents of 3 files.' in job.meta['feedback']

    def test_verify_contents_linked_dataset(self, mock_dataset_with_local_dir):
        class JobMock():
            def __init__(self):
                self.meta = dict()
            def save_meta(self):
                pass

        CURRENT_JOB = JobMock()

        def get_current_job_mock():
            return CURRENT_JOB

        with patch('gtmcore.dispatcher.jobs.get_current_job', side_effect=get_current_job_mock):
            ds = mock_dataset_with_local_dir[0]
            im = InventoryManager()

            ds.backend.update_from_remote(ds, lambda x: print(x))

            m = Manifest(ds, 'tester')
            assert len(m.manifest.keys()) == 4
            assert os.path.isfile(os.path.join(m.cache_mgr.cache_root, m.dataset_revision, 'test1.txt'))
            assert os.path.isfile(os.path.join(m.cache_mgr.cache_root, m.dataset_revision, 'test2.txt'))
            assert os.path.isfile(os.path.join(m.cache_mgr.cache_root, m.dataset_revision, 'subdir', 'test3.txt'))

            modified_items = ds.backend.verify_contents(ds, lambda x: print(x))
            assert len(modified_items) == 0

            lb = im.create_labbook("tester", "tester", 'test-labbook')
            im.link_dataset_to_labbook(f"{ds.root_dir}/.git", "tester", ds.name, lb, "tester")

            dataset_dir = os.path.join(lb.root_dir, '.gigantum', 'datasets', 'tester', ds.name)
            ds = im.load_dataset_from_directory(dataset_dir)

            test_dir = os.path.join(mock_dataset_with_local_dir[1], "local_data", "test_dir")
            with open(os.path.join(test_dir, 'test1.txt'), 'wt') as tf:
                tf.write("This file got changed in the filesystem")

            kwargs = {
                'logged_in_username': "tester",
                'access_token': "asdf",
                'id_token': "1234",
                'dataset_owner': "tester",
                'dataset_name': 'dataset-1',
                'labbook_owner': "tester",
                'labbook_name': 'test-labbook'
            }

            jobs.verify_dataset_contents(**kwargs)
            job = gtmcore.dispatcher.jobs.get_current_job()

            assert 'modified_keys' in job.meta
            assert job.meta['modified_keys'] == ["test1.txt"]
            assert 'Validating contents of 3 files.' in job.meta['feedback']

    def test_complete_dataset_upload_transaction_simple(self, mock_config_file_background_tests):
        im = InventoryManager(mock_config_file_background_tests[0])
        ds = im.create_dataset('default', 'default', "new-ds", storage_type="gigantum_object_v1", description="100")
        m = Manifest(ds, 'default')

        helper_append_file(m.cache_mgr.cache_root, m.dataset_revision, "test1.txt", "fake content!")
        helper_append_file(m.cache_mgr.cache_root, m.dataset_revision, "test2.txt", "moar fake content!")

        dl_kwargs = {
            'dispatcher': Dispatcher,
            'logged_in_username': "default",
            'logged_in_email': "default@gigantum.com",
            'dataset_owner': "default",
            'dataset_name': "new-ds",
            'config_file': mock_config_file_background_tests[0]
        }

        assert len(m.manifest) == 0
        gtmcore.dispatcher.dataset_jobs.complete_dataset_upload_transaction(**dl_kwargs)

        m = Manifest(ds, 'default')

        # make sure manifest got updated
        assert len(m.manifest) == 2
        assert 'test1.txt' in m.manifest
        assert 'test2.txt' in m.manifest

        assert m.manifest['test1.txt']['b'] == '13'
        assert len(m.manifest['test1.txt']['h']) == 128
        assert 'manifest-' in m.manifest['test1.txt']['fn']

        assert m.manifest['test2.txt']['b'] == '18'
        assert len(m.manifest['test2.txt']['h']) == 128
        assert 'manifest-' in m.manifest['test2.txt']['fn']

        assert m.manifest['test2.txt']['h'] != m.manifest['test1.txt']['h']

        # Make sure activity created
        assert len(ds.git.log()) == 6
        assert "_GTM_ACTIVITY_START_" in ds.git.log()[0]['message']
        assert "Uploaded 2 new file(s)." in ds.git.log()[0]['message']

    def test_complete_dataset_upload_transaction_overflow_batches(self, mock_config_file_background_tests):
        im = InventoryManager(mock_config_file_background_tests[0])
        ds = im.create_dataset('default', 'default', "new-ds", storage_type="gigantum_object_v1", description="100")
        m = Manifest(ds, 'default')

        helper_append_file(m.cache_mgr.cache_root, m.dataset_revision, "test1.txt", "fake content 1")
        helper_write_big_file(m.cache_mgr.cache_root, m.dataset_revision, "test2.dat", "12")
        helper_append_file(m.cache_mgr.cache_root, m.dataset_revision, "test3.txt", "fake content 3")
        helper_append_file(m.cache_mgr.cache_root, m.dataset_revision, "test4.txt", "fake content 4")
        helper_write_big_file(m.cache_mgr.cache_root, m.dataset_revision, "test5.dat", "12")
        helper_append_file(m.cache_mgr.cache_root, m.dataset_revision, "test6.txt", "fake content")
        helper_write_big_file(m.cache_mgr.cache_root, m.dataset_revision, "test7.dat", "23")
        helper_append_file(m.cache_mgr.cache_root, m.dataset_revision, "test8.txt", "fake content")

        dl_kwargs = {
            'dispatcher': Dispatcher,
            'logged_in_username': "default",
            'logged_in_email': "default@gigantum.com",
            'dataset_owner': "default",
            'dataset_name': "new-ds",
            'config_file': mock_config_file_background_tests[0]
        }

        assert len(m.manifest) == 0
        gtmcore.dispatcher.dataset_jobs.complete_dataset_upload_transaction(**dl_kwargs)

        m = Manifest(ds, 'default')

        # make sure manifest got updated
        assert len(m.manifest) == 8
        assert 'test1.txt' in m.manifest
        assert 'test2.dat' in m.manifest
        assert 'test3.txt' in m.manifest
        assert 'test4.txt' in m.manifest
        assert 'test5.dat' in m.manifest
        assert 'test6.txt' in m.manifest
        assert 'test7.dat' in m.manifest
        assert 'test8.txt' in m.manifest

        assert m.manifest['test1.txt']['b'] == '14'
        assert len(m.manifest['test1.txt']['h']) == 128
        assert 'manifest-' in m.manifest['test1.txt']['fn']

        assert m.manifest['test2.dat']['b'] == '2000000000'
        assert len(m.manifest['test2.dat']['h']) == 128
        assert 'manifest-' in m.manifest['test2.dat']['fn']

        assert m.manifest['test2.dat']['h'] == m.manifest['test5.dat']['h']
        assert m.manifest['test2.dat']['h'] != m.manifest['test7.dat']['h']

        # Make sure activity created
        assert len(ds.git.log()) == 6
        assert "_GTM_ACTIVITY_START_" in ds.git.log()[0]['message']
        assert "Uploaded 8 new file(s)." in ds.git.log()[0]['message']

    def test_complete_dataset_upload_transaction_all_types(self, mock_config_file_background_tests):
        im = InventoryManager(mock_config_file_background_tests[0])
        ds = im.create_dataset('default', 'default', "new-ds", storage_type="gigantum_object_v1", description="100")
        m = Manifest(ds, 'default')

        helper_append_file(m.cache_mgr.cache_root, m.dataset_revision, "test1.txt", "fake content 1")
        helper_append_file(m.cache_mgr.cache_root, m.dataset_revision, "test2.txt", "fake content 2")
        helper_append_file(m.cache_mgr.cache_root, m.dataset_revision, "test3.txt", "fake content 3")

        dl_kwargs = {
            'dispatcher': Dispatcher,
            'logged_in_username': "default",
            'logged_in_email': "default@gigantum.com",
            'dataset_owner': "default",
            'dataset_name': "new-ds",
            'config_file': mock_config_file_background_tests[0]
        }

        assert len(m.manifest) == 0
        gtmcore.dispatcher.dataset_jobs.complete_dataset_upload_transaction(**dl_kwargs)

        m = Manifest(ds, 'default')

        # make sure manifest got updated
        assert len(m.manifest) == 3
        assert 'test1.txt' in m.manifest
        assert 'test2.txt' in m.manifest
        assert 'test3.txt' in m.manifest
        hash1 = m.manifest['test1.txt']['h']

        # Make sure activity created
        assert len(ds.git.log()) == 6
        assert "_GTM_ACTIVITY_START_" in ds.git.log()[0]['message']
        assert "Uploaded 3 new file(s)." in ds.git.log()[0]['message']

        helper_append_file(m.cache_mgr.cache_root, m.dataset_revision, "test1.txt", "fake content changed")
        helper_append_file(m.cache_mgr.cache_root, m.dataset_revision, "test4.txt", "fake content 4")
        os.remove(os.path.join(m.cache_mgr.cache_root, m.dataset_revision, "test3.txt"))

        gtmcore.dispatcher.dataset_jobs.complete_dataset_upload_transaction(**dl_kwargs)
        m = Manifest(ds, 'default')

        # make sure manifest got updated
        assert len(m.manifest) == 3
        assert 'test1.txt' in m.manifest
        assert 'test2.txt' in m.manifest
        assert 'test4.txt' in m.manifest
        assert hash1 != m.manifest['test1.txt']['h']

        # Make sure activity created
        assert len(ds.git.log()) == 8
        assert "_GTM_ACTIVITY_START_" in ds.git.log()[0]['message']
        assert "Uploaded 1 new file(s). Uploaded 1 modified file(s). 1 deleted file(s)." in ds.git.log()[0]['message']

    def test_complete_dataset_upload_transaction_failure(self, mock_config_file_background_tests):
        im = InventoryManager(mock_config_file_background_tests[0])
        ds = im.create_dataset('default', 'default', "new-ds", storage_type="gigantum_object_v1", description="100")
        m = Manifest(ds, 'default')
        dispatcher_obj = Dispatcher()

        helper_write_big_file(m.cache_mgr.cache_root, m.dataset_revision, "test1.dat", "12")
        helper_write_big_file(m.cache_mgr.cache_root, m.dataset_revision, "test2.dat", "23")
        helper_append_file(m.cache_mgr.cache_root, m.dataset_revision, "zztest3.txt", "fake content 3")
        helper_append_file(m.cache_mgr.cache_root, m.dataset_revision, "zztest4.txt", "fake content 4")
        helper_append_file(m.cache_mgr.cache_root, m.dataset_revision, "zztest5.txt", "fake content 5")
        helper_append_file(m.cache_mgr.cache_root, m.dataset_revision, "zztest6.txt", "fake content 6")
        job_kwargs = {
            'dispatcher': Dispatcher,
            'logged_in_username': "default",
            'logged_in_email': "default@gigantum.com",
            'dataset_owner': "default",
            'dataset_name': "new-ds",
            'config_file': mock_config_file_background_tests[0]
        }

        job_metadata = {'dataset': f"default|default|new-ds",
                        'method': 'complete_dataset_upload_transaction'}
        assert len(m.manifest) == 0

        job_key = dispatcher_obj.dispatch_task(gtmcore.dispatcher.dataset_jobs.complete_dataset_upload_transaction,
                                               kwargs=job_kwargs,
                                               metadata=job_metadata)

        time.sleep(3)

        # Remove files to make them fail
        os.remove(os.path.join(m.cache_mgr.cache_root, m.dataset_revision, "zztest4.txt"))
        os.remove(os.path.join(m.cache_mgr.cache_root, m.dataset_revision, "zztest5.txt"))

        cnt = 0
        while cnt < 120:
            job_status = dispatcher_obj.query_task(job_key)

            if job_status.status == 'finished':
                break

            time.sleep(1)
            cnt += 1

        assert cnt < 119

        m = Manifest(ds, 'default')
        assert len(m.manifest) == 4
        assert 'test1.dat' in m.manifest
        assert 'test2.dat' in m.manifest
        assert 'zztest3.txt' in m.manifest
        assert 'zztest6.txt' in m.manifest
        assert 'zztest5.txt' not in m.manifest
        assert 'zztest4.txt' not in m.manifest

        assert job_status.meta['has_failures'] is True
        assert 'The following files failed to hash. Try re-uploading the files again:\nzztest4.txt \nzztest5.txt' ==\
               job_status.meta['failure_detail']
        assert 'An error occurred while processing some files. Check details and re-upload.' == \
               job_status.meta['feedback']

    def test_complete_dataset_upload_transaction_prune_job(self, mock_config_file_background_tests):
        im = InventoryManager(mock_config_file_background_tests[0])
        ds = im.create_dataset('default', 'default', "new-ds", storage_type="gigantum_object_v1", description="100")
        m = Manifest(ds, 'default')

        helper_append_file(m.cache_mgr.cache_root, m.dataset_revision, "test1.txt", "fake content!")

        dl_kwargs = {
            'dispatcher': Dispatcher,
            'logged_in_username': "default",
            'logged_in_email': "default@gigantum.com",
            'dataset_owner': "default",
            'dataset_name': "new-ds",
            'config_file': mock_config_file_background_tests[0]
        }

        assert len(m.manifest) == 0
        gtmcore.dispatcher.dataset_jobs.complete_dataset_upload_transaction(**dl_kwargs)

        m = Manifest(ds, 'default')

        # make sure manifest got updated
        assert len(m.manifest) == 1
        assert 'test1.txt' in m.manifest

        assert m.manifest['test1.txt']['b'] == '13'
        assert len(m.manifest['test1.txt']['h']) == 128
        assert 'manifest-' in m.manifest['test1.txt']['fn']

        # Make sure activity created
        assert len(ds.git.log()) == 6
        assert "_GTM_ACTIVITY_START_" in ds.git.log()[0]['message']
        assert "Uploaded 1 new file(s)." in ds.git.log()[0]['message']

    def test_check_and_import_dataset_exists(self, mock_config_file):
        im = InventoryManager(mock_config_file[0])
        ds = im.create_dataset('default', 'default', "dataset100", storage_type="gigantum_object_v1", description="100")

        # Fake publish to a local bare repo
        _MOCK_create_remote_repo2(ds, 'test', None, None)

        kwargs = {
            'logged_in_username': "default",
            'dataset_owner': "default",
            'dataset_name': "dataset100",
            'remote_url': ds.remote,
            'config_file': mock_config_file[0]
        }

        gtmcore.dispatcher.dataset_jobs.check_and_import_dataset(**kwargs)

    def test_check_and_import_dataset(self, mock_config_file):
        im = InventoryManager(mock_config_file[0])
        ds = im.create_dataset('default', 'default', "dataset100", storage_type="gigantum_object_v1", description="100")

        # Fake publish to a local bare repo
        _MOCK_create_remote_repo2(ds, 'test', None, None)
        remote_url = ds.remote

        im.delete_dataset('default', 'default', "dataset100")

        with pytest.raises(InventoryException):
            im.load_dataset('default', 'default', "dataset100")

        kwargs = {
            'logged_in_username': "default",
            'dataset_owner': "default",
            'dataset_name': "dataset100",
            'remote_url': remote_url,
            'config_file': mock_config_file[0]
        }

        gtmcore.dispatcher.dataset_jobs.check_and_import_dataset(**kwargs)

        ds = im.load_dataset('default', 'default', "dataset100")
        assert ds.name == 'dataset100'
        assert ds.namespace == 'default'

    def test_download_dataset_files(self, mock_config_file_background_tests, mock_dataset_head):
        def dispatch_query_mock(self, job_key):
            JobStatus = namedtuple("JobStatus", ['status', 'meta'])
            return JobStatus(status='finished', meta={'completed_bytes': '500'})

        def dispatch_mock(self, method_reference, kwargs, metadata, persist):
            with aioresponses() as mocked_responses:
                mocked_responses.get(f'https://api.gigantum.com/object-v1/{ds.namespace}/{ds.name}/{obj_id_1}',
                                     payload={
                                             "presigned_url": f"https://dummyurl.com/{obj_id_1}?params=1",
                                             "namespace": ds.namespace,
                                             "obj_id": obj_id_1,
                                             "dataset": ds.name
                                     },
                                     status=200)

                with open(obj1_source, 'rb') as data1:
                    mocked_responses.get(f"https://dummyurl.com/{obj_id_1}?params=1",
                                         body=data1.read(), status=200,
                                         content_type='application/octet-stream')
                gtmcore.dispatcher.dataset_jobs.pull_objects(**kwargs)

                return "afakejobkey"

        im = InventoryManager(mock_config_file_background_tests[0])
        ds = im.create_dataset('default', 'default', "dataset100", storage_type="gigantum_object_v1", description="100")
        m = Manifest(ds, 'default')
        iom = IOManager(ds, m)

        helper_append_file(m.cache_mgr.cache_root, m.dataset_revision, "test1.txt", "asdfadfsdf")
        m.sweep_all_changes()

        obj_to_push = iom.objects_to_push()
        assert len(obj_to_push) == 1
        _, obj_id_1 = obj_to_push[0].object_path.rsplit('/', 1)
        obj1_target = obj_to_push[0].object_path

        obj1_source = os.path.join('/tmp', uuid.uuid4().hex)

        assert os.path.exists(obj1_target) is True
        helper_compress_file(obj1_target, obj1_source)
        assert os.path.isfile(obj1_target) is False
        assert os.path.isfile(obj1_source) is True

        # Clear out from linked dir
        os.remove(os.path.join(m.cache_mgr.cache_root, m.dataset_revision, 'test1.txt'))

        with patch.object(Configuration, 'find_default_config', lambda self: mock_config_file_background_tests[0]):
            with patch.object(Dispatcher, 'dispatch_task', dispatch_mock):
                with patch.object(Dispatcher, 'query_task', dispatch_query_mock):
                    dl_kwargs = {
                        'logged_in_username': "default",
                        'access_token': "asdf",
                        'id_token': "1234",
                        'dataset_owner': "default",
                        'dataset_name': "dataset100",
                        'labbook_owner': None,
                        'labbook_name': None,
                        'keys': ["test1.txt"],
                        'config_file': mock_config_file_background_tests[0]
                    }

                    gtmcore.dispatcher.dataset_jobs.download_dataset_files(**dl_kwargs)
                    assert os.path.isfile(obj1_target) is True

                    decompressor = snappy.StreamDecompressor()
                    with open(obj1_source, 'rb') as dd:
                        source1 = decompressor.decompress(dd.read())
                        source1 += decompressor.flush()
                    with open(obj1_target, 'rt') as dd:
                        dest1 = dd.read()
                    assert source1.decode("utf-8") == dest1

    def test_download_dataset_files_file_fail(self, mock_config_file_background_tests):
        def dispatch_query_mock(self, job_key):
            # mock the job actually running and returning status
            JobStatus = namedtuple("JobStatus", ['status', 'meta'])
            return JobStatus(status='finished', meta={'completed_bytes': '0', 'failure_keys': 'test1.txt'})

        def dispatch_mock(self, method_reference, kwargs, metadata, persist):
                gtmcore.dispatcher.dataset_jobs.pull_objects(**kwargs)
                return "afakejobkey"

        im = InventoryManager(mock_config_file_background_tests[0])
        ds = im.create_dataset('default', 'default', "dataset100", storage_type="gigantum_object_v1", description="100")
        m = Manifest(ds, 'default')
        iom = IOManager(ds, m)

        helper_append_file(m.cache_mgr.cache_root, m.dataset_revision, "test1.txt", "asdfadfsdf")
        m.sweep_all_changes()

        obj_to_push = iom.objects_to_push()
        assert len(obj_to_push) == 1
        _, obj_id_1 = obj_to_push[0].object_path.rsplit('/', 1)
        obj1_target = obj_to_push[0].object_path

        obj1_source = os.path.join('/tmp', uuid.uuid4().hex)

        assert os.path.exists(obj1_target) is True
        helper_compress_file(obj1_target, obj1_source)
        assert os.path.isfile(obj1_target) is False
        assert os.path.isfile(obj1_source) is True

        # Clear out from linked dir
        os.remove(os.path.join(m.cache_mgr.cache_root, m.dataset_revision, 'test1.txt'))

        with patch.object(Configuration, 'find_default_config', lambda self: mock_config_file_background_tests[0]):
            with patch.object(Dispatcher, 'dispatch_task', dispatch_mock):
                with patch.object(Dispatcher, 'query_task', dispatch_query_mock):
                    dl_kwargs = {
                        'logged_in_username': "default",
                        'access_token': "asdf",
                        'id_token': "1234",
                        'dataset_owner': "default",
                        'dataset_name': "dataset100",
                        'labbook_owner': None,
                        'labbook_name': None,
                        'keys': ["test1.txt"],
                        'config_file': mock_config_file_background_tests[0]
                    }

                    with pytest.raises(IOError):
                        gtmcore.dispatcher.dataset_jobs.download_dataset_files(**dl_kwargs)
                    assert os.path.isfile(obj1_target) is False

    def test_download_dataset_files_job_fail(self, mock_config_file_background_tests):
        def dispatch_query_mock(self, job_key):
            # mock the job actually running and returning status
            JobStatus = namedtuple("JobStatus", ['status', 'meta'])
            return JobStatus(status='failed', meta={'completed_bytes': '0'})

        def dispatch_mock(self, method_reference, kwargs, metadata, persist):
                gtmcore.dispatcher.dataset_jobs.pull_objects(**kwargs)
                return "afakejobkey"

        im = InventoryManager(mock_config_file_background_tests[0])
        ds = im.create_dataset('default', 'default', "dataset100", storage_type="gigantum_object_v1", description="100")
        m = Manifest(ds, 'default')
        iom = IOManager(ds, m)

        helper_append_file(m.cache_mgr.cache_root, m.dataset_revision, "test1.txt", "asdfadfsdf")
        m.sweep_all_changes()

        obj_to_push = iom.objects_to_push()
        assert len(obj_to_push) == 1
        _, obj_id_1 = obj_to_push[0].object_path.rsplit('/', 1)
        obj1_target = obj_to_push[0].object_path

        obj1_source = os.path.join('/tmp', uuid.uuid4().hex)

        assert os.path.exists(obj1_target) is True
        helper_compress_file(obj1_target, obj1_source)
        assert os.path.isfile(obj1_target) is False
        assert os.path.isfile(obj1_source) is True

        # Clear out from linked dir
        os.remove(os.path.join(m.cache_mgr.cache_root, m.dataset_revision, 'test1.txt'))

        with patch.object(Configuration, 'find_default_config', lambda self: mock_config_file_background_tests[0]):
            with patch.object(Dispatcher, 'dispatch_task', dispatch_mock):
                with patch.object(Dispatcher, 'query_task', dispatch_query_mock):
                    dl_kwargs = {
                        'logged_in_username': "default",
                        'access_token': "asdf",
                        'id_token': "1234",
                        'dataset_owner': "default",
                        'dataset_name': "dataset100",
                        'labbook_owner': None,
                        'labbook_name': None,
                        'keys': ["test1.txt"],
                        'config_file': mock_config_file_background_tests[0]
                    }

                    with pytest.raises(IOError):
                        gtmcore.dispatcher.dataset_jobs.download_dataset_files(**dl_kwargs)
                    assert os.path.isfile(obj1_target) is False

    def test_push_objects(self, mock_config_file, mock_dataset_head):
        im = InventoryManager(mock_config_file[0])
        ds = im.create_dataset('default', 'default', "dataset100", storage_type="gigantum_object_v1", description="100")
        manifest = Manifest(ds, 'default')
        iom = IOManager(ds, manifest)

        revision = manifest.dataset_revision
        os.makedirs(os.path.join(manifest.cache_mgr.cache_root, revision, "other_dir"))
        helper_append_file(manifest.cache_mgr.cache_root, revision, "test1.txt", "test content 1")
        helper_append_file(manifest.cache_mgr.cache_root, revision, "test2.txt", "test content 2")
        manifest.sweep_all_changes()

        obj_to_push = iom.objects_to_push()
        assert len(obj_to_push) == 2
        _, obj1 = obj_to_push[0].object_path.rsplit('/', 1)
        _, obj2 = obj_to_push[1].object_path.rsplit('/', 1)

        with aioresponses() as mocked_responses:
            mocked_responses.put(f'https://api.gigantum.com/object-v1/{ds.namespace}/{ds.name}/{obj1}',
                                 payload={
                                     "presigned_url": f"https://dummyurl.com/{obj1}?params=1",
                                     "namespace": ds.namespace,
                                     "key_id": "hghghg",
                                     "obj_id": obj1,
                                     "dataset": ds.name
                                 },
                                 status=200)
            mocked_responses.put(f"https://dummyurl.com/{obj1}?params=1",
                                 payload={},
                                 status=200)

            mocked_responses.put(f'https://api.gigantum.com/object-v1/{ds.namespace}/{ds.name}/{obj2}',
                                 payload={
                                     "presigned_url": f"https://dummyurl.com/{obj2}?params=1",
                                     "namespace": ds.namespace,
                                     "key_id": "hghghg",
                                     "obj_id": obj2,
                                     "dataset": ds.name
                                 },
                                 status=200)
            mocked_responses.put(f"https://dummyurl.com/{obj2}?params=1",
                                 payload={},
                                 status=200)

            job_kwargs = {
                'objs': obj_to_push,
                'logged_in_username': "default",
                'access_token': "faketoken",
                'id_token': "faketoken",
                'dataset_owner': ds.namespace,
                'dataset_name': ds.name,
                'config_file': ds.client_config.config_file,
            }
            gtmcore.dispatcher.dataset_jobs.push_dataset_objects(**job_kwargs)
