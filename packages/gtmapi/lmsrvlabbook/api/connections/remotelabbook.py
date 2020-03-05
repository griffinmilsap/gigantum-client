import graphene
from lmsrvlabbook.api.objects.remotelabbook import RemoteLabbook


class RemoteLabbookConnection(graphene.relay.Connection):
    """A Connection for paging through remote labbooks.

    This is a remote call, so should be fetched on its own and only when needed. The user must have a valid
    session for data to be returned.

    Supported sorting modes:
        - az: naturally sort
        - created_on: sort by creation date, newest first
        - modified_on: sort by modification date, newest first
    """
    class Meta:
        node = RemoteLabbook


