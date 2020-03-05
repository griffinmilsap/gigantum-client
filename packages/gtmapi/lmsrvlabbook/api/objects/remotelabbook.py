import graphene

from gtmcore.inventory.inventory import InventoryManager, InventoryException

from lmsrvcore.api.interfaces import GitRepository
from lmsrvcore.auth.user import get_logged_in_username
from lmsrvcore.utilities import configure_git_credentials


class RemoteLabbook(graphene.ObjectType):
    """A type representing a LabBook stored on a remote server

    RemoteLabbooks are uniquely identified by both the "owner" and the "name" of the LabBook

    NOTE: RemoteLabbooks require all fields to be explicitly set as there is no current way to asynchronously retrieve
          the data

    """
    class Meta:
        interfaces = (graphene.relay.Node, GitRepository)

    # A short description of the LabBook limited to 140 UTF-8 characters
    description = graphene.String()

    # Whether it is public or private (or local only)
    visibility = graphene.String()

    # Creation date/timestamp in UTC in ISO format
    creation_date_utc = graphene.String()

    # Modification date/timestamp in UTC in ISO format
    modified_date_utc = graphene.String()

    # Flag indicating if the LabBook also exists locally
    is_local = graphene.Boolean()

    # Url to import the LabBook from the remote server
    import_url = graphene.String()

    @classmethod
    def get_node(cls, info, id):
        """Method to resolve the object based on it's Node ID"""
        # Parse the key
        owner, name = id.split("&")

        return RemoteLabbook(id="{}&{}".format(owner, name), name=name, owner=owner)

    def resolve_id(self, info):
        """Resolve the unique Node id for this object"""
        if not self.id:
            if not self.owner or not self.name:
                raise ValueError("Resolving a Remote Labbook Node ID requires owner and name to be set")
            self.id = f"{self.owner}&{self.name}"
        return self.id

    def resolve_visibility(self, info):
        mgr = configure_git_credentials()
        try:
            d = mgr.repo_details(namespace=self.owner, repository_name=self.name)
            return d.get('visibility')
        except ValueError:
            return "unknown"

    def resolve_description(self, info):
        """Return the description of the labbook"""
        if self.description is None:
            raise ValueError("RemoteLabbook requires all fields to be explicitly set")
        return self.description

    def resolve_creation_date_utc(self, info):
        """Return the creation timestamp

        Args:
            info:

        Returns:

        """
        if self.creation_date_utc is None:
            raise ValueError("RemoteLabbook requires all fields to be explicitly set")
        return self.creation_date_utc

    def resolve_modified_date_utc(self, info):
        """Return the modified timestamp

        Args:
            info:

        Returns:

        """
        if self.modified_date_utc is None:
            raise ValueError("RemoteLabbook requires all fields to be explicitly set")
        return self.modified_date_utc

    def resolve_is_local(self, info):
        """Return the modified timestamp

        Args:
            info:

        Returns:

        """
        try:
            username = get_logged_in_username()
            InventoryManager().load_labbook(username, self.owner, self.name)
            return True
        except InventoryException:
            return False

    def resolve_import_url(self, info):
        """Return the url to import the labbook

        Args:
            info:

        Returns:

        """
        if self.import_url is None:
            raise ValueError("RemoteLabbook requires all fields to be explicitly set")
        return self.import_url
