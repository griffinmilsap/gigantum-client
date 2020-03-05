import os
import pprint
import shutil
import tempfile
import pytest
import mock

from gtmcore.container import container_for_context
from gtmcore.dispatcher import jobs
from gtmcore.workflows import GitWorkflow, LabbookWorkflow
import gtmcore.fixtures
from gtmcore.fixtures.datasets import helper_append_file, helper_compress_file
from gtmcore.workflows import MergeOverride


from gtmcore.fixtures import mock_config_file, mock_config_with_repo, mock_labbook_lfs_disabled,\
    _MOCK_create_remote_repo2
from gtmcore.environment import ComponentManager
from gtmcore.inventory.inventory import InventoryManager
from gtmcore.inventory.branching import BranchManager
from gtmcore.imagebuilder import ImageBuilder

from gtmcore.dispatcher.tests import BG_SKIP_MSG, BG_SKIP_TEST


@pytest.mark.skipif(BG_SKIP_TEST, reason=BG_SKIP_MSG)
class TestJobs(object):
    def test_success_import_export_zip(self, mock_config_with_repo):

        # Create new LabBook to be exported
        im = InventoryManager(mock_config_with_repo[0])
        lb = im.create_labbook('unittester', 'unittester',
                                             "unittest-lb-for-export-import-test",
                                             description="Testing import-export.")
        cm = ComponentManager(lb)
        cm.add_base(gtmcore.fixtures.ENV_UNIT_TEST_REPO, gtmcore.fixtures.ENV_UNIT_TEST_BASE,
                    gtmcore.fixtures.ENV_UNIT_TEST_REV)

        ib = ImageBuilder(lb)
        ib.assemble_dockerfile()

        # Make sure the destination user exists locally
        working_dir = lb.client_config.config['git']['working_directory']
        os.makedirs(os.path.join(working_dir, 'unittester2', 'unittester2', 'labbooks'), exist_ok=True)

        lb_root = lb.root_dir
        with tempfile.TemporaryDirectory() as temp_dir_path:
            # Export the labbook
            export_dir = os.path.join(mock_config_with_repo[1], "export")
            exported_archive_path = jobs.export_labbook_as_zip(lb.root_dir, export_dir)
            tmp_archive_path = shutil.copy(exported_archive_path, '/tmp')

            # Delete the labbook
            shutil.rmtree(lb.root_dir)
            assert not os.path.exists(lb_root), f"LabBook at {lb_root} should not exist."

            assert os.path.exists(tmp_archive_path)
            # Now import the labbook as a new user, validating that the change of namespace works properly.
            imported_lb_path = jobs.import_labboook_from_zip(archive_path=tmp_archive_path, username='unittester2',
                                                             owner='unittester2', config_file=mock_config_with_repo[0])

            assert not os.path.exists(tmp_archive_path)
            tmp_archive_path = shutil.copy(exported_archive_path, '/tmp')
            assert os.path.exists(tmp_archive_path)

            # New path should reflect username of new owner and user.
            assert imported_lb_path == lb_root.replace('/unittester/unittester/', '/unittester2/unittester2/')
            import_lb = InventoryManager(mock_config_with_repo[0]).load_labbook_from_directory(imported_lb_path)

            ib = ImageBuilder(import_lb)
            ib.assemble_dockerfile(write=True)
            assert os.path.exists(os.path.join(imported_lb_path, '.gigantum', 'env', 'Dockerfile'))

            assert not import_lb.has_remote

            # Repeat the above, except with the original user (e.g., re-importing their own labbook)
            user_import_lb = jobs.import_labboook_from_zip(archive_path=tmp_archive_path, username="unittester",
                                                           owner="unittester", config_file=mock_config_with_repo[0])
            assert not os.path.exists(tmp_archive_path)

            # New path should reflect username of new owner and user.
            assert user_import_lb
            import_lb2 = InventoryManager(mock_config_with_repo[0]).load_labbook_from_directory(user_import_lb)
            # After importing, the new user (in this case "cat") should be the current, active workspace.
            # And be created, if necessary.
            assert not import_lb2.has_remote

            build_kwargs = {
                'path': lb.root_dir,
                'username': 'unittester',
                'nocache': True
            }
            docker_image_id = jobs.build_labbook_image(**build_kwargs)
            try:
                project_container = container_for_context('unittester')
                project_container.delete_image(docker_image_id)
            except Exception as e:
                pprint.pprint(e)
                raise

    def test_import_labbook_from_remote(self, mock_config_with_repo, monkeypatch):
        def _mock_import_labbook_from_remote(remote, username, config_file):
            print('X' * 200)
            lb = InventoryManager(config_file).create_labbook(username, username, remote.repo_name)
            return LabbookWorkflow(lb)

        monkeypatch.setattr(LabbookWorkflow, 'import_from_remote', _mock_import_labbook_from_remote)
        # Mock out actual import, as it's already tested in workflows.
        root_dir = jobs.import_labbook_from_remote('http://mocked-url.com/unittester/mock-labbook', 'unittester',
                                                   config_file=mock_config_with_repo[0])
        assert '/labbooks/' in root_dir
        assert 'mock-labbook' == root_dir.split('/')[-1]

    def test_success_import_export_lbk(self, mock_config_with_repo):
        """Test legacy .lbk extension still works"""
        # Create new LabBook to be exported
        lb = InventoryManager(mock_config_with_repo[0]).create_labbook('unittester', 'unittester',
                                                                       "unittest-lb-for-export-import-test-lbk",
                                                                       description="Testing import-export.")
        cm = ComponentManager(lb)
        cm.add_base(gtmcore.fixtures.ENV_UNIT_TEST_REPO, gtmcore.fixtures.ENV_UNIT_TEST_BASE,
                    gtmcore.fixtures.ENV_UNIT_TEST_REV)

        ib = ImageBuilder(lb)
        ib.assemble_dockerfile()

        # Make sure the destination user exists locally
        working_dir = lb.client_config.config['git']['working_directory']
        os.makedirs(os.path.join(working_dir, 'unittester2', 'unittester2', 'labbooks'), exist_ok=True)

        lb_root = lb.root_dir
        with tempfile.TemporaryDirectory() as temp_dir_path:
            # Export the labbook
            export_dir = os.path.join(mock_config_with_repo[1], "export")
            exported_archive_path = jobs.export_labbook_as_zip(lb.root_dir, export_dir)
            tmp_archive_path = shutil.copy(exported_archive_path, '/tmp')

            lbk_archive_path = tmp_archive_path.replace(".zip", ".lbk")
            lbk_archive_path = shutil.copy(tmp_archive_path, lbk_archive_path)

            # Delete the labbook
            shutil.rmtree(lb.root_dir)
            assert not os.path.exists(lb_root), f"LabBook at {lb_root} should not exist."

            assert os.path.exists(tmp_archive_path)
            # Now import the labbook as a new user, validating that the change of namespace works properly.
            imported_lb_path = jobs.import_labboook_from_zip(archive_path=lbk_archive_path, username='unittester2',
                                                             owner='unittester2', config_file=mock_config_with_repo[0])

            assert not os.path.exists(lbk_archive_path)
            tmp_archive_path = shutil.copy(exported_archive_path, '/tmp')
            assert os.path.exists(tmp_archive_path)

            # New path should reflect username of new owner and user.
            assert imported_lb_path == lb_root.replace('/unittester/unittester/', '/unittester2/unittester2/')
            import_lb = InventoryManager(mock_config_with_repo[0]).load_labbook_from_directory(imported_lb_path)

            ib = ImageBuilder(import_lb)
            ib.assemble_dockerfile(write=True)
            assert os.path.exists(os.path.join(imported_lb_path, '.gigantum', 'env', 'Dockerfile'))

            assert not import_lb.has_remote

    def test_fail_import_export_zip(self, mock_config_with_repo):

        # Create new LabBook to be exported
        lb = InventoryManager(mock_config_with_repo[0]).create_labbook('test', 'test',
                                                                       "lb-fail-export-import-test",
                                                                       description="Failing import-export.")
        cm = ComponentManager(lb)
        cm.add_base(gtmcore.fixtures.ENV_UNIT_TEST_REPO, gtmcore.fixtures.ENV_UNIT_TEST_BASE,
                    gtmcore.fixtures.ENV_UNIT_TEST_REV)

        lb_root = lb.root_dir
        with tempfile.TemporaryDirectory() as temp_dir_path:
            # Export the labbook
            export_dir = os.path.join(mock_config_with_repo[1], "export")
            try:
                exported_archive_path = jobs.export_labbook_as_zip("/tmp", export_dir)
                assert False, "Exporting /tmp should fail"
            except Exception as e:
                pass

            # Export the labbook, then remove before re-importing
            exported_archive_path = jobs.export_labbook_as_zip(lb.root_dir, export_dir)

            try:
                imported_lb_path = jobs.import_labboook_from_zip(archive_path=exported_archive_path, username="test",
                                                                 owner="test", config_file=mock_config_with_repo[0])
                assert False, f"Should not be able to import LabBook because it already exited at {lb_root}"
            except Exception as e:
                pass

            try:
                imported_lb_path = jobs.import_labboook_from_zip(archive_path="/t", username="test",
                                                                 owner="test", config_file=mock_config_with_repo[0])
                assert False, f"Should not be able to import LabBook from strange directory /t"
            except Exception as e:
                pass

    @mock.patch('gtmcore.workflows.gitworkflows_utils.create_remote_gitlab_repo', new=_MOCK_create_remote_repo2)
    def test_publish_respository(self, mock_labbook_lfs_disabled):
        """Test a simple publish and ensuring master is active branch. """
        username = 'test'
        lb = mock_labbook_lfs_disabled[2]
        bm = BranchManager(lb, username)
        assert bm.branches_remote == []
        assert bm.branches_local == ['master']

        jobs.publish_repository(lb, username=username, access_token='fake', id_token='fake-too')

        assert os.path.exists(lb.remote)

        # Assert that publish only pushes up the master branch.
        assert bm.branches_local == ['master']
        assert bm.branches_remote == ['master']

    @mock.patch('gtmcore.workflows.gitworkflows_utils.create_remote_gitlab_repo', new=_MOCK_create_remote_repo2)
    def test_sync_repository(self, mock_labbook_lfs_disabled):
        username = 'test'
        lb = mock_labbook_lfs_disabled[2]
        bm = BranchManager(lb, username)
        assert bm.branches_remote == []
        assert bm.branches_local == ['master']

        jobs.publish_repository(lb, username=username, access_token='fake', id_token='fake-too')

        assert os.path.exists(lb.remote)

        # Assert that publish only pushes up the master branch.
        assert bm.branches_local == ['master']
        assert bm.branches_remote == ['master']

        assert bm.get_commits_ahead('master') == 0
        assert bm.get_commits_behind('master') == 0

        lb.write_readme("do a commit")

        assert bm.get_commits_ahead('master') == 1
        assert bm.get_commits_behind('master') == 0

        jobs.sync_repository(lb, username=username, override=MergeOverride.OURS,
                             access_token='fake', id_token='fake-too')

        assert bm.get_commits_ahead('master') == 0
        assert bm.get_commits_behind('master') == 0
