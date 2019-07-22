import pytest
import os
import glob
import uuid
import shutil
from aioresponses import aioresponses
import responses

from gtmcore.inventory.branching import BranchManager
from gtmcore.dataset.io.manager import IOManager
from gtmcore.fixtures.datasets import mock_dataset_with_cache_dir, mock_dataset_with_manifest, helper_append_file,\
    USERNAME, helper_compress_file, mock_dataset_with_manifest_bg_tests
from gtmcore.fixtures.fixtures import _create_temp_work_dir, mock_config_file_background_tests
from gtmcore.dataset.io import PushResult, PushObject


def chunk_update_callback(completed_chunk: bool):
    """Mock callback for collecting chunk feedback"""
    assert completed_chunk is True


@pytest.fixture()
def mock_dataset_head():
    """A pytest fixture that creates a dataset in a temp working dir. Deletes directory after test"""
    with responses.RequestsMock() as rsps:
        rsps.add(responses.HEAD, 'https://api.gigantum.com/object-v1/tester/dataset-1',
                 headers={'x-access-level': 'a'}, status=200)
        yield


class TestIOManager(object):
    def test_init(self, mock_dataset_with_manifest):
        ds, manifest, working_dir = mock_dataset_with_manifest
        iom = IOManager(ds, manifest)
        assert isinstance(iom, IOManager)
        assert isinstance(iom.push_dir, str)

    def test_objects_to_push(self, mock_dataset_with_manifest):
        ds, manifest, working_dir = mock_dataset_with_manifest
        iom = IOManager(ds, manifest)

        revision = manifest.dataset_revision
        os.makedirs(os.path.join(manifest.cache_mgr.cache_root, revision, "other_dir"))
        helper_append_file(manifest.cache_mgr.cache_root, revision, "test1.txt", "test content 1")
        helper_append_file(manifest.cache_mgr.cache_root, revision, "test2.txt", "test content 2")
        helper_append_file(manifest.cache_mgr.cache_root, revision, "other_dir/test4.txt", "test content 4")
        manifest.sweep_all_changes()

        # Modify file to have 2 objects with same key
        helper_append_file(manifest.cache_mgr.cache_root, iom.manifest.dataset_revision, "test2.txt", "test content 22")
        manifest.sweep_all_changes()

        obj_to_push = iom.objects_to_push()

        assert len(obj_to_push) == 4
        assert obj_to_push[0].dataset_path == "other_dir/test4.txt"
        assert obj_to_push[1].dataset_path == "test1.txt"
        assert obj_to_push[2].dataset_path == "test2.txt"
        assert obj_to_push[3].dataset_path == "test2.txt"
        assert obj_to_push[2].revision != obj_to_push[3].revision

        assert iom.num_objects_to_push() == 4

    def test_objects_to_push_deduped(self, mock_dataset_with_manifest):
        ds, manifest, working_dir = mock_dataset_with_manifest
        iom = IOManager(ds, manifest)

        revision = manifest.dataset_revision
        os.makedirs(os.path.join(manifest.cache_mgr.cache_root, revision, "other_dir"))
        helper_append_file(manifest.cache_mgr.cache_root, revision, "test1.txt", "test content dup")
        helper_append_file(manifest.cache_mgr.cache_root, revision, "test2.txt", "test content dup")
        helper_append_file(manifest.cache_mgr.cache_root, revision, "test3.txt", "test content dup")
        helper_append_file(manifest.cache_mgr.cache_root, revision, "other_dir/test4.txt", "test content 4")
        manifest.sweep_all_changes()

        # Write a .DS_Store file in the objects dir to make sure it gets skipped
        with open(os.path.join(manifest.cache_mgr.cache_root, 'objects', '.push', '.DS_Store'), 'wt') as ff:
            ff.write("")

        obj_to_push = iom.objects_to_push(remove_duplicates=True)

        assert len(obj_to_push) == 2
        assert obj_to_push[0].dataset_path == "other_dir/test4.txt"
        assert obj_to_push[1].dataset_path == "test1.txt"

        assert iom.num_objects_to_push(remove_duplicates=True) == 2

    def test_objects_to_push_ignore_other_branch(self, mock_dataset_with_manifest):
        ds, manifest, working_dir = mock_dataset_with_manifest
        iom = IOManager(ds, manifest)

        revision = manifest.dataset_revision
        os.makedirs(os.path.join(manifest.cache_mgr.cache_root, revision, "other_dir"))
        helper_append_file(manifest.cache_mgr.cache_root, revision, "test1.txt", "test content 1")
        helper_append_file(manifest.cache_mgr.cache_root, revision, "test2.txt", "fdsfgfd")
        manifest.sweep_all_changes()

        obj_to_push = iom.objects_to_push()
        assert len(obj_to_push) == 2
        assert obj_to_push[0].dataset_path == "test1.txt"
        assert obj_to_push[1].dataset_path == "test2.txt"

        # Create new branch and add a file there
        bm = BranchManager(ds, username=USERNAME)
        starting_branch = bm.active_branch
        bm.create_branch(title="test-branch")
        assert bm.active_branch == "test-branch"
        assert ds.is_repo_clean is True

        helper_append_file(manifest.cache_mgr.cache_root, iom.manifest.dataset_revision, "test3.txt", "fdsfgfd")
        manifest.sweep_all_changes()

        obj_to_push = iom.objects_to_push()
        assert len(obj_to_push) == 3
        assert obj_to_push[0].dataset_path == "test1.txt"
        assert obj_to_push[1].dataset_path == "test2.txt"
        assert obj_to_push[2].dataset_path == "test3.txt"

        # Go back to original branch, you shouldn't have to push file on other branch
        bm.workon_branch(starting_branch)

        obj_to_push = iom.objects_to_push()
        assert len(obj_to_push) == 2
        assert obj_to_push[0].dataset_path == "test1.txt"
        assert obj_to_push[1].dataset_path == "test2.txt"

    def test_push_objects(self, mock_dataset_with_manifest, mock_dataset_head):
        ds, manifest, working_dir = mock_dataset_with_manifest
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
            mocked_responses.head(f'https://api.gigantum.com/object-v1/{ds.namespace}/{ds.name}',
                                  headers={
                                         "presigned_url": f"https://dummyurl.com/{obj1}?params=1",
                                         "namespace": ds.namespace,
                                         "key_id": "hghghg",
                                         "obj_id": obj1,
                                         "dataset": ds.name
                                  },
                                  status=200)
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
                                 headers={'Etag': 'asdfasdf'},
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
                                 headers={'Etag': '12341234'},
                                 status=200)

            assert len(glob.glob(f'{iom.push_dir}/*')) == 1
            iom.dataset.backend.set_default_configuration("test-user", "abcd", '1234')

            result = iom.push_objects(obj_to_push, chunk_update_callback)
            assert len(glob.glob(f'{iom.push_dir}/*')) == 1

            assert len(result.success) == 2
            assert len(result.failure) == 0
            assert isinstance(result, PushResult) is True
            assert isinstance(result.success[0], PushObject) is True
            assert result.success[0].object_path != result.success[1].object_path
            assert result.success[0].object_path in [obj_to_push[0].object_path, obj_to_push[1].object_path]
            assert result.success[1].object_path in [obj_to_push[0].object_path, obj_to_push[1].object_path]

    def test_push_objects_deduplicate(self, mock_dataset_with_manifest, mock_dataset_head):
        ds, manifest, working_dir = mock_dataset_with_manifest
        iom = IOManager(ds, manifest)

        revision = manifest.dataset_revision
        os.makedirs(os.path.join(manifest.cache_mgr.cache_root, revision, "other_dir"))
        helper_append_file(manifest.cache_mgr.cache_root, revision, "test1.txt", "test content 1")
        helper_append_file(manifest.cache_mgr.cache_root, revision, "test2.txt", "test content dup")
        helper_append_file(manifest.cache_mgr.cache_root, revision, "test3.txt", "test content dup")
        manifest.sweep_all_changes()

        obj_to_push = iom.objects_to_push()
        assert len(obj_to_push) == 3
        _, obj1 = obj_to_push[0].object_path.rsplit('/', 1)
        _, obj2 = obj_to_push[1].object_path.rsplit('/', 1)
        _, obj3 = obj_to_push[2].object_path.rsplit('/', 1)
        assert obj1 != obj2
        assert obj2 == obj3

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
                                 headers={'Etag': 'asdfasdf'},
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
                                 headers={'Etag': '12341234'},
                                 status=200)

            assert len(glob.glob(f'{iom.push_dir}/*')) == 1
            iom.dataset.backend.set_default_configuration("test-user", "abcd", '1234')

            obj_to_push = iom.objects_to_push(remove_duplicates=True)
            result = iom.push_objects(obj_to_push, chunk_update_callback)
            assert len(glob.glob(f'{iom.push_dir}/*')) == 1

            assert len(result.success) == 2
            assert len(result.failure) == 0
            assert isinstance(result, PushResult) is True
            assert isinstance(result.success[0], PushObject) is True
            assert result.success[0].object_path != result.success[1].object_path
            assert result.success[0].object_path in [obj_to_push[0].object_path, obj_to_push[1].object_path]
            assert result.success[1].object_path in [obj_to_push[0].object_path, obj_to_push[1].object_path]

    def test_push_objects_with_failure(self, mock_dataset_with_manifest, mock_dataset_head):
        ds, manifest, working_dir = mock_dataset_with_manifest
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
                                 headers={'Etag': 'asdfasdf'},
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
                                 status=500)
            mocked_responses.put(f"https://dummyurl.com/{obj2}?params=1",
                                 payload={},
                                 status=500)
            mocked_responses.put(f"https://dummyurl.com/{obj2}?params=1",
                                 payload={},
                                 status=500)
    
            assert len(glob.glob(f'{iom.push_dir}/*')) == 1
            iom.dataset.backend.set_default_configuration("test-user", "abcd", '1234')
    
            result = iom.push_objects(obj_to_push, chunk_update_callback)
            assert len(glob.glob(f'{iom.push_dir}/*')) == 1

            assert len(result.success) == 1
            assert len(result.failure) == 1
            assert result.success[0].object_path == obj_to_push[0].object_path
            assert result.failure[0].object_path == obj_to_push[1].object_path

    def test_pull_objects(self, mock_dataset_with_manifest, mock_dataset_head):
        def chunk_update_callback(completed_bytes: int):
            """Method to update the job's metadata and provide feedback to the UI"""
            assert type(completed_bytes) == int
            assert completed_bytes > 0

        ds, manifest, working_dir = mock_dataset_with_manifest
        iom = IOManager(ds, manifest)

        revision = manifest.dataset_revision
        os.makedirs(os.path.join(manifest.cache_mgr.cache_root, revision, "other_dir"))
        helper_append_file(manifest.cache_mgr.cache_root, revision, "test1.txt", "test content 1")
        helper_append_file(manifest.cache_mgr.cache_root, revision, "test2.txt", "test content 2")
        manifest.sweep_all_changes()

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

            assert len(glob.glob(f'{iom.push_dir}/*')) == 1
            iom.dataset.backend.set_default_configuration("test-user", "abcd", '1234')

            result = iom.pull_objects(keys=["test1.txt"], progress_update_fn=chunk_update_callback)
            assert len(glob.glob(f'{iom.push_dir}/*')) == 1
            assert len(result.success) == 1
            assert len(result.failure) == 0
            assert result.success[0].object_path == obj_to_push[0].object_path

            assert os.path.isfile(obj1_target) is True
            assert os.path.isfile(obj2_target) is False
            with open(obj1_target, 'rt') as dd:
                assert "test content 1" == dd.read()

            result = iom.pull_objects(keys=["test2.txt"], progress_update_fn=chunk_update_callback)
            assert len(glob.glob(f'{iom.push_dir}/*')) == 1
            assert len(result.success) == 1
            assert len(result.failure) == 0
            assert result.success[0].object_path == obj_to_push[1].object_path

            assert os.path.isfile(obj1_target) is True
            assert os.path.isfile(obj2_target) is True
            with open(obj1_target, 'rt') as dd:
                assert "test content 1" == dd.read()
            with open(obj2_target, 'rt') as dd:
                assert "test content 2" == dd.read()

    def test__get_pull_all_keys(self, mock_dataset_with_manifest):
        ds, manifest, working_dir = mock_dataset_with_manifest
        iom = IOManager(ds, manifest)

        revision = manifest.dataset_revision
        os.makedirs(os.path.join(manifest.cache_mgr.cache_root, revision, "other_dir"))
        helper_append_file(manifest.cache_mgr.cache_root, revision, "other_dir/test3.txt", "dummy content")
        helper_append_file(manifest.cache_mgr.cache_root, revision, "test1.txt", "test content 1")
        helper_append_file(manifest.cache_mgr.cache_root, revision, "test2.txt", "test content 2")
        manifest.sweep_all_changes()

        obj_to_push = iom.objects_to_push()
        assert len(obj_to_push) == 3
        obj3 = obj_to_push[0].object_path
        obj1 = obj_to_push[1].object_path
        obj2 = obj_to_push[2].object_path

        rev_dir = os.path.join(manifest.cache_mgr.cache_root, manifest.dataset_revision)
        file3 = os.path.join(rev_dir, obj_to_push[0].dataset_path)
        file1 = os.path.join(rev_dir, obj_to_push[1].dataset_path)
        file2 = os.path.join(rev_dir, obj_to_push[2].dataset_path)

        assert os.path.exists(obj1) is True
        assert os.path.exists(obj2) is True
        assert os.path.exists(obj3) is True
        assert os.path.exists(file1) is True
        assert os.path.exists(file2) is True
        assert os.path.exists(file3) is True

        result = iom._get_pull_all_keys()
        assert len(result) == 0

        # Completely remove other_dir/test3.txt object
        os.remove(obj3)
        os.remove(file3)

        # Remove link for test1.txt, should relink automatically and not need to be pulled
        os.remove(file1)

        assert os.path.exists(obj1) is True
        assert os.path.exists(obj2) is True
        assert os.path.exists(obj3) is False
        assert os.path.exists(file1) is False
        assert os.path.exists(file2) is True
        assert os.path.exists(file3) is False

        result = iom._get_pull_all_keys()
        assert len(result) == 1
        assert result[0] == 'other_dir/test3.txt'

        assert os.path.exists(obj1) is True
        assert os.path.exists(obj2) is True
        assert os.path.exists(obj3) is False
        assert os.path.exists(file1) is True
        assert os.path.exists(file2) is True
        assert os.path.exists(file3) is False

    def test_compute_pull_batches(self, mock_dataset_with_manifest_bg_tests):
        ds, manifest, working_dir = mock_dataset_with_manifest_bg_tests
        iom = IOManager(ds, manifest)

        revision = manifest.dataset_revision
        os.makedirs(os.path.join(manifest.cache_mgr.cache_root, revision, "other_dir"))
        helper_append_file(manifest.cache_mgr.cache_root, revision, "other_dir/test3.txt", "test content 3")
        helper_append_file(manifest.cache_mgr.cache_root, revision, "test1.txt", "test" * 4300000)
        helper_append_file(manifest.cache_mgr.cache_root, revision, "test2.txt", "test content 2")
        helper_append_file(manifest.cache_mgr.cache_root, revision, "test4.txt", "test content 4")
        helper_append_file(manifest.cache_mgr.cache_root, revision, "test5.txt", "test content 5")
        manifest.sweep_all_changes()

        with pytest.raises(ValueError):
            iom.compute_pull_batches()

        # Remove all files so everything needs to be pulled
        rev_dir = os.path.join(manifest.cache_mgr.cache_root, manifest.dataset_revision)
        object_dir = os.path.join(manifest.cache_mgr.cache_root, 'objects')
        shutil.rmtree(rev_dir)
        shutil.rmtree(object_dir)

        key_batches, total_bytes, num_files = iom.compute_pull_batches(pull_all=True)
        assert num_files == 5
        assert total_bytes == (4*4300000) + (14*4)
        assert len(key_batches) == 2
        assert len(key_batches[0]) == 4
        assert len(key_batches[1]) == 1
        assert key_batches[1][0] == 'test1.txt'

    def test_compute_push_batches(self, mock_dataset_with_manifest_bg_tests):
        """Test compute push batches, verifying it works OK when you've deleted some files"""
        ds, manifest, working_dir = mock_dataset_with_manifest_bg_tests
        iom = IOManager(ds, manifest)

        revision = manifest.dataset_revision
        os.makedirs(os.path.join(manifest.cache_mgr.cache_root, revision, "other_dir"))
        helper_append_file(manifest.cache_mgr.cache_root, revision, "other_dir/test3.txt", "test content 3")
        helper_append_file(manifest.cache_mgr.cache_root, revision, "test1.txt", "test" * 4300000)
        helper_append_file(manifest.cache_mgr.cache_root, revision, "test2.txt", "test content 2")
        helper_append_file(manifest.cache_mgr.cache_root, revision, "test4.txt", "test content 4")
        helper_append_file(manifest.cache_mgr.cache_root, revision, "test5.txt", "test content 5")
        manifest.sweep_all_changes()

        assert len(manifest.manifest) == 6

        # remove a file from the manifest
        manifest.delete(['test5.txt'])
        assert len(manifest.manifest) == 5

        key_batches, total_bytes, num_files = iom.compute_push_batches()
        assert num_files == 5
        assert total_bytes == (4*4300000) + (14*4)
        assert len(key_batches) == 2
        assert len(key_batches[0]) == 4
        assert len(key_batches[1]) == 1
        assert key_batches[1][0].dataset_path == 'test1.txt'
