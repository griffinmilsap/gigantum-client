import os
import flask
import graphene

from lmsrvcore.api.objects.user import UserIdentity

from lmsrvcore.auth.identity import get_identity_manager_instance
from gtmcore.logging import LMLogger

logger = LMLogger.get_logger()


class RemoveUserIdentity(graphene.relay.ClientIDMutation):
    """Mutation to remove a locally stored user identity (no-op if not running in local mode)"""

    # Return the Note
    user_identity_edge = graphene.Field(lambda: UserIdentity)

    @classmethod
    def mutate_and_get_payload(cls, root, input, client_mutation_id=None):
        # Call the logout method to remove any locally stored data
        get_identity_manager_instance().logout()

        # Wipe current user from request context
        flask.g.user_obj = None
        flask.g.id_token = None
        flask.g.access_token = None

        return RemoveUserIdentity(user_identity_edge=UserIdentity())
