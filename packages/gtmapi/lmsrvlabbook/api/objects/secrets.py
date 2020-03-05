import graphene

from gtmcore.labbook import SecretStore
from gtmcore.logging import LMLogger

from lmsrvcore.api.interfaces import GitRepository
from lmsrvcore.auth.user import get_logged_in_username

logger = LMLogger.get_logger()


class SecretFileMapping(graphene.ObjectType):
    """Represents a secret vault - i.e., a directory that contains secret key files. """
    class Meta:
        interfaces = (graphene.relay.Node, GitRepository)

    # Name of the secrets file.
    filename = graphene.String()

    # Path **inside the running project container**
    mount_path = graphene.String()

    # Determine if an actual file is present in the secret store
    is_present = graphene.Boolean()

    @classmethod
    def get_node(cls, info, id):
        """Method to resolve the object based on its Node ID"""
        # Parse the key
        owner, name, filename = id.split("&")

        return SecretFileMapping(id=f"{owner}&{name}&{filename}",
                                 name=name, owner=owner, filename=filename)

    def resolve_id(self, info):
        """Resolve the unique Node id for this object"""
        if not self.owner or not self.name:
            raise ValueError("Resolving a Environment Node ID requires owner and name to be set")

        return f"{self.owner}&{self.name}&{self.filename}"

    def _helper_resolve_mount_path(self, labbook):
        secret_store = SecretStore(labbook, get_logged_in_username())
        return secret_store[self.filename]

    def resolve_mount_path(self, info):
        return info.context.labbook_loader.load(f"{get_logged_in_username()}&{self.owner}&{self.name}").then(
            lambda labbook: self._helper_resolve_mount_path(labbook))

    def _helper_resolve_is_present(self, labbook):
        secret_store = SecretStore(labbook, get_logged_in_username())
        if self.filename in secret_store:
            return (self.filename, True) in secret_store.list_files()
        else:
            return False

    def resolve_is_present(self, info):
        return info.context.labbook_loader.load(f"{get_logged_in_username()}&{self.owner}&{self.name}").then(
            lambda labbook: self._helper_resolve_is_present(labbook))
