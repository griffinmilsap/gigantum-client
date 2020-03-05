import pytest
import shutil
import tempfile
import subprocess
import os
from pkg_resources import resource_filename

from gtmcore.inventory.inventory  import InventoryManager
from gtmcore.configuration import Configuration
from gtmcore.workflows import ZipExporter, ZipWorkflowException

from gtmcore.fixtures import (mock_config_file, mock_labbook_lfs_disabled,
                              mock_duplicate_labbook, remote_bare_repo,
                              sample_src_file, mock_config_lfs_disabled)


class TestLabbookImportZipping(object):
    def test_fail_import_garbled(self, mock_config_file):
        # Baseline state of gigantum dir (used to check no new files created)
        snapshot = str(list(sorted(os.walk(mock_config_file[1]))))
        z = ZipExporter()
        
        # Test with a non-existing file
        with pytest.raises(ZipWorkflowException):
            z.import_labbook('nonsense.zip', 'none', 'none', mock_config_file[0])
        assert snapshot == str(list(sorted(os.walk(mock_config_file[1]))))

        # Test with an invalid zip file
        with open('/tmp/invalid.zip', 'wb') as x:
            x.write(b'Invalid zip file content. ' * 500)
        with pytest.raises(ZipWorkflowException):
            z.import_labbook(x.name, 'none', 'none', mock_config_file[0])
        assert snapshot == str(list(sorted(os.walk(mock_config_file[1]))))

    def test_fail_import_non_labbook_zip_single_file(self, mock_config_file):
        # Test a valid zip file but one that does not contain project

        # make a zip of a single file
        with open('/tmp/single_file_zip.file', 'wb') as f:
            f.write(b'abc123' * 500)
        subprocess.run('zip -r single_file_zip.zip single_file_zip.file'.split(),
                       check=True, cwd='/tmp')
        assert os.path.isfile('/tmp/single_file_zip.zip')

        # Baseline state of gigantum dir (used to check no new files created)
        snapshot = str(list(sorted(os.walk(mock_config_file[1]))))
        z = ZipExporter()
        with pytest.raises(ZipWorkflowException):
            z.import_labbook('/tmp/single_file_zip.zip', 'test', 'test', mock_config_file[0])

    def test_fail_import_non_labbook_zip_directory(self, mock_config_file):
        # Test a valid zip file but one that does not contain project

        # make a zip of a directory
        dirs = ['code', '.git', '.gigantum', '.labbook', 'input', 'output']
        for d in dirs:
            os.makedirs(os.path.join('/tmp/non-lb-dir', d), exist_ok=True)
            with open(os.path.join('/tmp/non-lb-dir', d, 'file.f'), 'wb') as f:
                f.write(b'file content. ' * 40)
        subprocess.run('zip -r non-lb-dir.zip non-lb-dir'.split(),
                       check=True, cwd='/tmp')

        # Baseline state of gigantum dir (used to check no new files created)
        pre_snapshot = str(list(sorted(os.walk(mock_config_file[1]))))
        z = ZipExporter()
        with pytest.raises(ZipWorkflowException):
            z.import_labbook('/tmp/non-lb-dir.zip', 'test', 'test', mock_config_file[0])
        post_snapshot = str(list(sorted(os.walk(mock_config_file[1]))))
        assert pre_snapshot == post_snapshot

    def test_fail_export_garbled_export(self):
        # Test giving a path that doesn't exist
        with pytest.raises(ZipWorkflowException):
            ZipExporter.export_labbook('/not/a/real/path', '.')

    def test_fail_export_not_a_labbook(self):
        # Pass in a valid directory, but one that is not an LB
        with pytest.raises(ZipWorkflowException):
            ZipExporter.export_labbook('/var', '.')

    def test_success_import_valid_labbook_from_windows(self, mock_config_file):
        import_zip = os.path.join(resource_filename('gtmcore','workflows/tests'),
                                  'test_from_windows.zip')
        dup_import = shutil.copy(import_zip, '/tmp/copy-of-test_from_windows.zip')

        workspace = Configuration(mock_config_file[0]).config['git']['working_directory']

        # Snapshots of directories before and after import - assert different
        pre_snapshot = str(list(sorted(os.walk(workspace))))
        z = ZipExporter()
        x = z.import_labbook(dup_import, 'test', 'test', mock_config_file[0])
        post_snapshot = str(list(sorted(os.walk(workspace))))
        assert pre_snapshot != post_snapshot

    def test_success_import_valid_labbook_from_macos(self, mock_config_file):
        import_zip = os.path.join(resource_filename('gtmcore','workflows/tests'),
                                  'snappy.zip')
        assert os.path.exists(import_zip)
        dup_import = shutil.copy(import_zip, '/tmp/copy-of-snappy.zip')

        workspace = Configuration(mock_config_file[0]).config['git']['working_directory']

        # Snapshots of directories before and after import - assert different
        pre_snapshot = str(list(sorted(os.walk(workspace))))
        z = ZipExporter()
        x = z.import_labbook(dup_import, 'test', 'test', mock_config_file[0])
        post_snapshot = str(list(sorted(os.walk(workspace))))
        assert pre_snapshot != post_snapshot

    def test_fail_cannot_import_labbook_to_overwrite_name(self, mock_config_file):
        import_zip = os.path.join(resource_filename('gtmcore','workflows'),
                                  'tests', 'snappy.zip')
        dup_import = shutil.copy(import_zip, '/tmp/copy-of-snappy.zip')
        z = ZipExporter()
        x = z.import_labbook(dup_import, 'test', 'test', mock_config_file[0])

        dup_import = shutil.copy(import_zip, '/tmp/copy-of-snappy.zip')
        # Now try to import that again and it should fail, cause a
        # project by that name already exists.
        with pytest.raises(ZipWorkflowException):
            y = z.import_labbook(dup_import, 'test', 'test', mock_config_file[0])

    def test_success_export_then_import_different_users(self, mock_config_file):
        inv_manager = InventoryManager(mock_config_file[0])
        lb = inv_manager.create_labbook('unittester', 'unittester', 'unittest-zip')

        with tempfile.TemporaryDirectory() as tempd:
            path = ZipExporter.export_labbook(lb.root_dir, tempd)
            newlb = ZipExporter.import_labbook(path, "unittester2", "unittester2",
                                               mock_config_file[0])
            assert not os.path.exists(path)
            assert 'unittester2' == InventoryManager(mock_config_file[0]).query_owner(newlb)
            assert newlb.is_repo_clean

            # Now try with same user as exporter
            path2 = ZipExporter.export_labbook(lb.root_dir, tempd)
            shutil.rmtree(lb.root_dir)
            lb2 = ZipExporter.import_labbook(path2, "unittester", "unittester",
                                             mock_config_file[0])
            assert 'unittester' == InventoryManager(mock_config_file[0]).query_owner(lb2)
            assert lb2.is_repo_clean
