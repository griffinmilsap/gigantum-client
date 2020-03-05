from typing import Optional
import os
import json
import jose
import redis_lock
from redis import StrictRedis

from gtmcore.auth.identity import IdentityManager, User, AuthenticationError
from gtmcore.configuration import Configuration

from gtmcore.logging import LMLogger
logger = LMLogger.get_logger()


class LocalIdentityManager(IdentityManager):
    """Class for authenticating a user and accessing user identity while supporting local, offline operation"""

    def __init__(self, config_obj: Configuration) -> None:
        """Constructor"""
        # Call super constructor
        IdentityManager.__init__(self, config_obj=config_obj)

        self.auth_dir = os.path.join(self.config.config['git']['working_directory'], '.labmanager', 'identity')

        self._lock_redis_client: Optional[StrictRedis] = None

    # Override the user property to automatically try to load the user from disk
    @property
    def user(self) -> Optional[User]:
        if self._user:
            return self._user
        else:
            return self._load_user(None)

    @user.setter
    def user(self, value: User) -> None:
        self._user = value

    def is_authenticated(self, access_token: Optional[str] = None, id_token: Optional[str] = None) -> bool:
        """Method to check if the user is currently authenticated in the context of this identity manager

        Args:
            access_token(str): API access JSON web token from Auth0
            id_token(str): ID JSON web token from Auth0

        Returns:
            bool
        """
        user = self._load_user(id_token)
        if user:
            return True
        else:
            is_valid = self.is_token_valid(access_token)
            if is_valid:
                # Load the user profile now so the user doesn't have to log in again later
                self.get_user_profile(access_token, id_token)

            return is_valid

    def is_token_valid(self, access_token: Optional[str] = None) -> bool:
        """Method to check if the user's Auth0 session is still valid

        Returns:
            bool
        """
        if not access_token:
            return False
        else:
            try:
                _ = self.validate_jwt_token(access_token, self.config.config['auth']['audience'])
            except AuthenticationError:
                return False

            return True

    def get_user_profile(self, access_token: Optional[str] = None, id_token: Optional[str] = None) -> Optional[User]:
        """Method to get the current logged in user profile info

        Args:
            access_token(str): API JSON web token from Auth0
            id_token(str): ID JSON web token from Auth0

        Returns:
            User
        """
        # Check if user is already loaded or stored locally
        user = self._load_user(id_token)
        if user:
            return user
        else:
            if not id_token:
                err_dict = {"code": "missing_token",
                            "description": "JWT must be provided if no locally stored identity is available"}
                raise AuthenticationError(err_dict, 401)

            # Validate JWT token
            token_payload = self.validate_jwt_token(id_token, self.config.config['auth']['client_id'],
                                                    access_token=access_token)

            # Create user identity instance
            user = User()
            user.email = self._get_profile_attribute(token_payload, "email", required=True)
            user.username = self._get_profile_attribute(token_payload, "nickname", required=True)
            user.given_name = self._get_profile_attribute(token_payload, "given_name", required=False)
            user.family_name = self._get_profile_attribute(token_payload, "family_name", required=False)
            self.user = user

            # Save User to local storage
            self._safe_cached_id_access(id_token)

            # Check if it's the first time this user has logged into this instance
            self._check_first_login(self.user.username, access_token, id_token)

            return self._user

    def logout(self) -> None:
        """Method to logout a user if applicable

        Returns:
            None
        """
        # Removed cached identity.
        data_file = os.path.join(self.auth_dir, 'cached_id_jwt')
        if os.path.exists(data_file):
            os.remove(data_file)

        # Remove the public key. If it even happens to get updated, this is a path to automatically fix
        data_file = os.path.join(self.auth_dir, 'jwks.json')
        if os.path.exists(data_file):
            os.remove(data_file)

        # Remove Git credentials file so you don't leak tokens between users.
        git_credentials_file = os.path.expanduser('~/.git-credentials')
        if os.path.exists(git_credentials_file):
            os.remove(git_credentials_file)

        self.user = None
        self.rsa_key = None
        logger.info("Removed user identity from local storage.")

    def _load_user(self, id_token: Optional[str]) -> Optional[User]:
        """Method to load a users's ID token from disk

        Returns:
            None
        """
        current_cached_id_token = self._safe_cached_id_access()
        if current_cached_id_token:
            if id_token is not None and id_token != current_cached_id_token:
                old_user = jose.jwt.get_unverified_claims(current_cached_id_token)['nickname']
                new_user = jose.jwt.get_unverified_claims(id_token)['nickname']
                if old_user == new_user:
                    logger.info(f"ID Token has been updated for {old_user}.")
                    self._safe_cached_id_access(id_token)

                    current_cached_id_token = id_token
                else:
                    logger.warning("ID Token user does not match locally cached identity! Clearing cached file.")
                    self._safe_cached_id_access("")
                    return None

            # Load data from JWT with limited checks due to possible timeout and lack of access token
            token_payload = self.validate_jwt_token(current_cached_id_token, self.config.config['auth']['client_id'],
                                                    limited_validation=True)

            # Create user identity instance
            user_obj = User()
            user_obj.email = self._get_profile_attribute(token_payload, "email", required=True)
            user_obj.username = self._get_profile_attribute(token_payload, "nickname", required=True)
            user_obj.given_name = self._get_profile_attribute(token_payload, "given_name", required=False)
            user_obj.family_name = self._get_profile_attribute(token_payload, "family_name", required=False)

            return user_obj
        else:
            return None

    def _safe_cached_id_access(self, id_token: Optional[str] = None) -> Optional[str]:
        """Method to read/write the ID Token cache file in a thread-safe way to prevent corruption and issues with
        multiple logins

        Args:
            id_token: The id token from Auth0

        Returns:
            str
        """
        lock: redis_lock.Lock = None
        try:
            lock_config = self.config.config['lock']

            # Get a redis client
            if not self._lock_redis_client:
                self._lock_redis_client = StrictRedis(host=lock_config['redis']['host'],
                                                      port=lock_config['redis']['port'],
                                                      db=lock_config['redis']['db'])

            # Get a lock object
            lock = redis_lock.Lock(self._lock_redis_client, "filesystem_lock|cached_id_jwt_update",
                                   expire=lock_config['expire'],
                                   auto_renewal=lock_config['auto_renewal'],
                                   strict=lock_config['redis']['strict'])

            cached_id_file = os.path.join(self.auth_dir, 'cached_id_jwt')
            if lock.acquire(timeout=lock_config['timeout']):
                try:
                    if id_token is not None:
                        if id_token == "":
                            os.remove(cached_id_file)
                            logger.warning(f"Removed cached ID token")
                        else:
                            # Update the id token cache file's contents
                            if not os.path.exists(self.auth_dir):
                                # Create directory to store user info if it doesn't exist
                                os.makedirs(self.auth_dir)

                            # If user data exists, remove it first
                            if os.path.exists(cached_id_file):
                                os.remove(cached_id_file)
                                logger.warning(f"User identity data already exists. Overwriting")

                            with open(cached_id_file, 'wt') as user_file:
                                json.dump(id_token, user_file)
                    else:
                        # read the ID
                        if os.path.exists(cached_id_file):
                            with open(cached_id_file, 'rt') as user_file:
                                id_token = json.load(user_file)

                        else:
                            id_token = None
                except:
                    # If any error occurs, blow the cached file away to prevent infinite login loops
                    logger.error(f"Cached user identity appears to be corrupted. Clearing files for recovery.")
                    if os.path.exists(cached_id_file):
                        os.remove(cached_id_file)
                    raise
            else:
                raise IOError(f"Could not acquire file system lock within {lock_config['timeout']} seconds. Failed "
                              f"to update cached user identity for offline mode. Log out and then log in to continue.")

            return id_token
        finally:
            # Release the Lock
            if lock:
                try:
                    lock.release()
                except redis_lock.NotAcquired as e:
                    # if you didn't get the lock and an error occurs, you probably won't be able to release, so log.
                    logger.error(e)
