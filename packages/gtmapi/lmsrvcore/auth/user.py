import flask

from gtmcore.logging import LMLogger
from gtmcore.auth.user import User
from gtmcore.gitlib.git import GitAuthor
from lmsrvcore.auth.identity import get_identity_manager_instance


def get_logged_in_user() -> User:
    """A method to get the current logged in User object"""
    request_scoped_user = flask.g.get('user_obj', None)
    if not request_scoped_user:
        access_token = flask.g.get('access_token', None)
        id_token = flask.g.get('id_token', None)

        request_scoped_user = get_identity_manager_instance().get_user_profile(access_token, id_token)
        flask.g.user_obj = request_scoped_user

    return request_scoped_user


def get_logged_in_username() -> str:
    """A Method to get the current logged in user's username


    Returns:
        str
    """
    user = get_logged_in_user()

    if not user:
        logger = LMLogger()
        logger.logger.error("Failed to load a user identity from request context.")
        raise ValueError("Failed to load a user identity from request context.")

    return user.username


def get_logged_in_author():
    """A Method to get the current logged in user's GitAuthor instance


    Returns:
        GitAuthor
    """
    user = get_logged_in_user()

    if not user:
        logger = LMLogger()
        logger.logger.error("Failed to load a user identity from request context.")
        raise ValueError("Failed to load a user identity from request context.")

    # Create a GitAuthor instance if possible

    return GitAuthor(name=user.username, email=user.email)
