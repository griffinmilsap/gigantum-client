import pytest
import os

from gtmcore.fixtures import mock_config_file_with_auth
from gtmcore.configuration import Configuration
from gtmcore.auth.identity import get_identity_manager, IdentityManager
from gtmcore.auth.local import LocalIdentityManager
from gtmcore.auth import User


class TestIdentity(object):
    def test_user_obj(self):
        """Manipulating user object"""
        u = User()

        assert u.username is None
        assert u.email is None
        assert u.given_name is None
        assert u.family_name is None

        u.username = "test"
        u.email = "test@test.com"
        u.given_name = "Testy"
        u.family_name = "McTestface"

        assert u.username == "test"
        assert u.email == "test@test.com"
        assert u.given_name == "Testy"
        assert u.family_name == "McTestface"

    def test_get_identity_manager_errors(self, mock_config_file_with_auth):
        """Testing get_identity_manager error handling"""
        config = Configuration(mock_config_file_with_auth[0])
        config.config['auth']['identity_manager'] = "asdfasdf"

        with pytest.raises(ValueError):
            get_identity_manager(config)

        del config.config['auth']['identity_manager']

        with pytest.raises(ValueError):
            get_identity_manager(config)

        del config.config['auth']

        with pytest.raises(ValueError):
            get_identity_manager(config)

    def test_get_identity_manager(self, mock_config_file_with_auth):
        """test getting an identity manager"""
        config = Configuration(mock_config_file_with_auth[0])

        mgr = get_identity_manager(config)

        assert type(mgr) == LocalIdentityManager
        assert mgr.config == config
        assert mgr.auth_dir == os.path.join(mock_config_file_with_auth[2], '.labmanager', 'identity')
        assert mgr.user is None
        assert mgr.rsa_key is None
        assert mgr._user is None
        assert mgr.is_anonymous("asdfasefd") is False
