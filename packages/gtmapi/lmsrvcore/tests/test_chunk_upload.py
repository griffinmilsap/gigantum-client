import pytest
import graphene
import os

from lmsrvcore.tests.fixtures import fixture_working_dir_with_cached_user
from lmsrvcore.api.mutations import ChunkUploadMutation
from gtmcore.configuration import Configuration


class MyMutation(graphene.relay.ClientIDMutation, ChunkUploadMutation):
    class Arguments:
        var = graphene.String()

    @classmethod
    def mutate_and_process_upload(cls, info, upload_file_path, upload_filename, **kwargs):
        return "success"


class TestChunkUpload(object):
    def test_get_temp_filename(self):
        """Test getting the filename"""
        mut = MyMutation()
        assert mut.get_temp_filename("asdf", "1234.txt") == os.path.join(Configuration().upload_dir, "asdf-1234.txt")

    def test_get_safe_filename(self):
        """Test getting safe filenames"""
        mut = MyMutation()
        assert mut.py_secure_filename("\n\ttest.txt") == "test.txt"
        assert mut.py_secure_filename(u'\x00' + f"test.txt") == "test.txt"

        assert mut.py_secure_filename("../../../test.txt") == "test.txt"
        assert mut.py_secure_filename("./test.txt") == "test.txt"
        assert mut.py_secure_filename("./../test.txt") == "test.txt"
        assert mut.py_secure_filename("../test.txt") == "test.txt"
        assert mut.py_secure_filename("/../test.txt") == "test.txt"

        assert mut.py_secure_filename("code/dir/test讀.txt") == "code/dir/test讀.txt"
        assert mut.py_secure_filename("code/dir/t*est讀.txt讀") == "code/dir/t_est讀.txt讀"
        assert mut.py_secure_filename("code/dir/test<>.txt") == 'code/dir/test__.txt'
        assert mut.py_secure_filename("code/dir<>/test.txt") == "code/dir__/test.txt"
        assert mut.py_secure_filename("code/dir<>/\\/:*|?test.txt") == "code/dir__/_/____test.txt"

    def test_validate_args(self):
        """Test errors on bad args"""
        mut = MyMutation()

        args = {
                  "upload_id": "dsffghfdsahgf",
                  "chunk_size": 100,
                  "total_chunks": 2,
                  "chunk_index": 3,
                  "file_size": "200",
                  "filename": "test.txt"
                }

        with pytest.raises(ValueError):
            mut.validate_args(args)

        args = {
                  "upload_id": "dsffghfdsahgf",
                  "chunk_size": 100,
                  "total_chunks": 2,
                  "chunk_index": 1,
                  "file_size": "1000",
                  "filename": "test.txt"
                }

        with pytest.raises(ValueError):
            mut.validate_args(args)

    def test_no_file(self):
        """Test error on no file"""
        class DummyContext(object):
            def __init__(self):
                self.files = {'blah': None}

        class DummyInfo(object):
            def __init__(self):
                self.context = DummyContext()

        mut = MyMutation()

        args = {
                  "upload_id": "dsffghfdsahgf",
                  "chunk_size": 100,
                  "total_chunks": 2,
                  "chunk_index": 1,
                  "file_size_kb": 200,
                  "filename": "test.txt"
                }

        with pytest.raises(ValueError):
            mut.mutate_and_get_payload(None, DummyInfo(), **{"chunk_upload_params": args})
