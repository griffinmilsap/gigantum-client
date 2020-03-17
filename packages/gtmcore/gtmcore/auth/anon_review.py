from typing import Optional

from gtmcore.logging import LMLogger
from gtmcore.auth.identity import User, AuthenticationError
from gtmcore.auth.anonymous import AnonymousIdentityManager

logger = LMLogger.get_logger()


class AnonymousReviewIdentityManager(AnonymousIdentityManager):
    """Class that only allows anonymous use, with access_token checked against a secret

    The access_token can be populated with a hash-arg like https://...#access_token=1234. It is
    not currently encoded into a psuedo-JWT, in order to simplify reading directly from the deploy
    script or the config file itself.

    The secret token is generally set in the config file with top level key `anon_review_secret`.
    (Being top-level makes it easier to simply append the secret to an existing config.)
    """

    @property
    def allow_server_access(self) -> bool:
        """Anonymous review does not provide access to the Hub

        Returns:
            bool
        """
        return False

    def is_authenticated(self, access_token: Optional[str] = None, id_token: Optional[str] = None) -> bool:
        """Once we get past the hash-arg check, we are always authenticated

        Args:
            access_token: checked via self.is_anonymous()
            id_token: ignored

        Returns:
            bool
        """
        if not access_token:
            # If no access token, no anonymous access
            return False

        return self.is_anonymous(access_token)

    def is_anonymous(self, access_token: str) -> bool:
        """In anonymous review, we are always / only anonymous

        Args:
            access_token: checked against the anon_review_secret

        Returns:
            True
        """
        secret = str(self.config.config["anon_review_secret"])
        return access_token == secret

    def is_token_valid(self, access_token: Optional[str] = None) -> bool:
        """Method to check if the user's access token session is still valid

        access_token: checked via self.is_anonymous()

        Returns:
            bool
        """
        if not access_token:
            return False

        return self.is_anonymous(access_token)

    def get_user_profile(self, access_token: Optional[str] = None, id_token: Optional[str] = None) -> Optional[User]:
        """Return the anonymous user if the access_token matches

        Args:
            access_token: checked against self.is_anonymous()
            id_token: ignored

        Returns:
            User
        """
        if not access_token:
            err_dict = {"code": "missing_token",
                        "description": "access_token must be provided for anonymous access"}
            raise AuthenticationError(err_dict, 401)

        if self.is_anonymous(access_token):
            # Create user identity instance
            self.user = self.anon_user
        else:
            err_dict = {"code": "wrong_token",
                        "description": "access_token must match client configuration for anonymous access"}
            raise AuthenticationError(err_dict, 401)

        return self.user
