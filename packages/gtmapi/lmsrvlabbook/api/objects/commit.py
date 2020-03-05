from typing import Optional
import graphene

from gtmcore.inventory.inventory import InventoryManager
from gtmcore.inventory.branching import BranchManager
from lmsrvcore.auth.identity import get_identity_manager_instance

from lmsrvcore.auth.user import get_logged_in_username
from lmsrvcore.api.interfaces import GitCommit, GitRepository
from lmsrvcore.utilities import configure_git_credentials
from lmsrvlabbook.dataloader.fetch import FetchLoader


class LabbookCommit(graphene.ObjectType):
    """An object representing a commit to a LabBook"""
    class Meta:
        interfaces = (graphene.relay.Node, GitRepository, GitCommit)

    @classmethod
    def get_node(cls, info, id):
        """Method to resolve the object based on it's Node ID"""
        # Parse the key
        owner, name, hash_str = id.split("&")

        return LabbookCommit(id=f"{owner}&{name}&{hash_str}", name=name, owner=owner,
                             hash=hash_str)

    def resolve_id(self, info):
        """Resolve the unique Node id for this object"""
        if not self.id:
            if not self.owner or not self.name or not self.hash:
                raise ValueError("Resolving a LabbookCommit Node ID requires owner, name, and hash to be set")
            self.id = f"{self.owner}&{self.name}&{self.hash}"

    def resolve_short_hash(self, info):
        """Resolve the short_hash field"""
        return self.hash[:8]

    def resolve_committed_on(self, info):
        """Resolve the committed_on field"""
        return info.context.labbook_loader.load(f"{get_logged_in_username()}&{self.owner}&{self.name}").then(
            lambda labbook: labbook.git.repo.commit(self.hash).committed_datetime.isoformat())


class Branch(graphene.ObjectType):
    """ Represents a branch in the repo """
    class Meta:
        interfaces = (graphene.relay.Node, GitRepository)

    _fetch_loader: Optional[FetchLoader] = None

    branch_name = graphene.String(required=True)

    # If true, indicates this branch is currently checked out
    is_active = graphene.Boolean()

    # Indicates whether this branch exists in the local repo
    is_local = graphene.Boolean()

    # Indicates whether this branch exists remotely
    is_remote = graphene.Boolean()

    # Indicates whether this branch can be merged into the current active branch
    is_mergeable = graphene.Boolean()

    # Count of commits on remote not present in local branch
    commits_behind = graphene.Int()

    # Count of commits on local branch not present in remote.
    commits_ahead = graphene.Int()

    @classmethod
    def get_node(cls, info, id):
        owner, labbook_name, branch_name = id.split('&')
        return Branch(owner=owner, name=labbook_name, branch_name=branch_name)

    def resolve_id(self, info):
        return '&'.join((self.owner, self.name, self.branch_name))

    def resolve_is_active(self, info):
        lb = InventoryManager().load_labbook(get_logged_in_username(),
                                             self.owner,
                                             self.name)
        return BranchManager(lb).active_branch == self.branch_name

    def resolve_is_local(self, info):
        lb = InventoryManager().load_labbook(get_logged_in_username(),
                                             self.owner,
                                             self.name)
        return self.branch_name in BranchManager(lb).branches_local

    def resolve_is_remote(self, info):
        lb = InventoryManager().load_labbook(get_logged_in_username(),
                                             self.owner,
                                             self.name)
        return self.branch_name in BranchManager(lb).branches_remote

    def resolve_is_mergeable(self, info):
        lb = InventoryManager().load_labbook(get_logged_in_username(),
                                             self.owner,
                                             self.name)
        mergeable = self.branch_name in BranchManager(lb).branches_local \
                    and self.branch_name != BranchManager(lb).active_branch

        return mergeable

    def resolve_commits_ahead(self, info):
        if not get_identity_manager_instance().allow_server_access:
            return 0
        else:
            logged_in_user = get_logged_in_username()
            lb = InventoryManager().load_labbook(logged_in_user,
                                                 self.owner,
                                                 self.name)
            configure_git_credentials()
            bm = BranchManager(lb)
            if self._fetch_loader:
                return self._fetch_loader.load(f"labbook&{logged_in_user}&{self.owner}&{self.name}").then(
                    lambda _: bm.get_commits_ahead(branch_name=self.branch_name))
            else:
                return bm.get_commits_ahead(branch_name=self.branch_name)

    def resolve_commits_behind(self, info):
        if not get_identity_manager_instance().allow_server_access:
            return 0
        else:
            logged_in_user = get_logged_in_username()
            lb = InventoryManager().load_labbook(logged_in_user,
                                                 self.owner,
                                                 self.name)
            configure_git_credentials()
            bm = BranchManager(lb)
            if self._fetch_loader:
                return self._fetch_loader.load(f"labbook&{logged_in_user}&{self.owner}&{self.name}").then(
                    lambda _: bm.get_commits_behind(branch_name=self.branch_name))
            else:
                return bm.get_commits_behind(branch_name=self.branch_name)

