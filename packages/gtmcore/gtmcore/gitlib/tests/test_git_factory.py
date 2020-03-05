import pytest
from gtmcore.gitlib.tests.git_interface_mixin import mock_config_filesystem
from gtmcore.gitlib import get_git_interface, GitFilesystem


class TestGitFactory(object):

    def test_invalid(self, mock_config_filesystem):
        """Test trying to get an invalid interface"""
        mock_config_filesystem["backend"] = "alkjshdfhkjlasdf"
        with pytest.raises(ValueError):
            get_git_interface(mock_config_filesystem)

        del mock_config_filesystem["backend"]
        with pytest.raises(ValueError):
            get_git_interface(mock_config_filesystem)

    def test_filesystem(self, mock_config_filesystem):
        """Test trying to get the filesystem interface"""
        git = get_git_interface(mock_config_filesystem)
        assert isinstance(git, GitFilesystem)
        assert git.repo is None
