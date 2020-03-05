import graphene

from gtmcore.logging import LMLogger
from gtmcore.inventory.inventory import InventoryManager
from gtmcore.inventory.branching import BranchManager
from gtmcore.activity import ActivityStore, ActivityDetailRecord, ActivityDetailType, ActivityRecord, ActivityType
from gtmcore.activity.utils import ImmutableDict, TextData, DetailRecordList, ImmutableList
from gtmcore.workflows import LabbookWorkflow, MergeOverride
from gtmcore.labbook import LabBook

from lmsrvcore.auth.user import get_logged_in_username, get_logged_in_author
from lmsrvlabbook.api.objects.labbook import Labbook

logger = LMLogger.get_logger()


class CreateExperimentalBranch(graphene.relay.ClientIDMutation):
    """Mutation to create a local experimental (or Rollback) branch. """

    class Input:
        owner = graphene.String(required=True)
        labbook_name = graphene.String(required=True)
        branch_name = graphene.String(required=True)
        revision = graphene.String()
        description = graphene.String()

    labbook = graphene.Field(Labbook)

    @classmethod
    def _update_branch_description(cls, lb: LabBook, description: str):
        # Update the description on branch creation
        lb.description = description
        lb.git.add(lb.config_path)
        commit = lb.git.commit('Updating description')

        adr = ActivityDetailRecord(ActivityDetailType.LABBOOK,
                                   show=False,
                                   data=TextData('plain', description))

        ar = ActivityRecord(ActivityType.LABBOOK,
                            message="Updated description of Project",
                            linked_commit=commit.hexsha,
                            tags=ImmutableList(["labbook"]),
                            show=False,
                            detail_objects=DetailRecordList([adr]))

        ars = ActivityStore(lb)
        ars.create_activity_record(ar)

    @classmethod
    def mutate_and_get_payload(cls, root, info, owner, labbook_name, branch_name, revision=None,
                               description=None, client_mutation_id=None):
        username = get_logged_in_username()
        lb = InventoryManager().load_labbook(username, owner, labbook_name,
                                             author=get_logged_in_author())
        with lb.lock():
            bm = BranchManager(lb, username=username)
            full_branch_title = bm.create_branch(title=branch_name,
                                                 revision=revision)

            logger.info(f"In {str(lb)} created new experimental feature branch: "
                        f"{full_branch_title}")

            if description:
                cls._update_branch_description(lb, description)

        return CreateExperimentalBranch(Labbook(id="{}&{}".format(owner, labbook_name),
                                                name=labbook_name, owner=owner))


class DeleteExperimentalBranch(graphene.relay.ClientIDMutation):
    """Delete a feature/rollback branch. Fails for any other attempt."""

    class Input:
        owner = graphene.String(required=True)
        labbook_name = graphene.String(required=True)
        branch_name = graphene.String(required=True)
        delete_local = graphene.Boolean(required=False, default=False)
        delete_remote = graphene.Boolean(required=False, default=False)

    labbook = graphene.Field(Labbook)

    @classmethod
    def mutate_and_get_payload(cls, root, info, owner, labbook_name, branch_name, delete_local=False,
                               delete_remote=False, client_mutation_id=None):
        username = get_logged_in_username()
        lb = InventoryManager().load_labbook(username, owner, labbook_name,
                                             author=get_logged_in_author())
        with lb.lock():
            bm = BranchManager(lb, username=username)
            if delete_local:
                bm.remove_branch(target_branch=branch_name)
            if delete_remote:
                bm.remove_remote_branch(target_branch=branch_name)
        return DeleteExperimentalBranch(Labbook(id="{}&{}".format(owner, labbook_name),
                                                name=labbook_name, owner=owner))


class WorkonBranch(graphene.relay.ClientIDMutation):
    """Work on another branch (perform a git checkout)."""

    class Input:
        owner = graphene.String(required=True)
        labbook_name = graphene.String(required=True)
        branch_name = graphene.String(required=True)
        revision = graphene.String()

    labbook = graphene.Field(Labbook)

    @classmethod
    def mutate_and_get_payload(cls, root, info, owner, labbook_name, branch_name, client_mutation_id=None):
        username = get_logged_in_username()
        lb = InventoryManager().load_labbook(username, owner, labbook_name,
                                             author=get_logged_in_author())
        with lb.lock():
            wf = LabbookWorkflow(lb)
            wf.checkout(username, branch_name)
        return WorkonBranch(Labbook(id="{}&{}".format(owner, labbook_name),
                                    name=labbook_name, owner=owner))


class ResetBranchToRemote(graphene.relay.ClientIDMutation):
    """ Undo all local history and then set current branch tip to match remote.

    Very useful when changes are made to master that cannot be pushed. """

    class Input:
        owner = graphene.String(required=True)
        labbook_name = graphene.String(required=True)

    labbook = graphene.Field(Labbook)

    @classmethod
    def mutate_and_get_payload(cls, root, info, owner, labbook_name, client_mutation_id=None):
        username = get_logged_in_username()
        lb = InventoryManager().load_labbook(username, owner, labbook_name,
                                             author=get_logged_in_author())
        with lb.lock():
            wf = LabbookWorkflow(lb)
            wf.reset(username)

        return ResetBranchToRemote(Labbook(id="{}&{}".format(owner, labbook_name),
                                           name=labbook_name, owner=owner))


class MergeFromBranch(graphene.relay.ClientIDMutation):
    """Merge from another branch into the current active branch. Force if necessary. """

    class Input:
        owner = graphene.String(required=True)
        labbook_name = graphene.String(required=True)
        other_branch_name = graphene.String(required=True)
        override_method = graphene.String(default="abort")

    labbook = graphene.Field(Labbook)

    @classmethod
    def mutate_and_get_payload(cls, root, info, owner, labbook_name, other_branch_name,
                               override_method="abort", client_mutation_id=None):
        username = get_logged_in_username()
        lb = InventoryManager().load_labbook(username, owner, labbook_name,
                                             author=get_logged_in_author())
        with lb.lock():
            override = MergeOverride(override_method)
            bm = BranchManager(lb, username=username)
            if override == MergeOverride.ABORT:
                bm.merge_from(other_branch=other_branch_name)
            elif override == MergeOverride.OURS:
                bm.merge_use_ours(other_branch=other_branch_name)
            elif override == MergeOverride.THEIRS:
                bm.merge_use_theirs(other_branch=other_branch_name)
            else:
                raise ValueError(f"Unknown override method {override}")

            # Run update_linked_datasets() to initialize and cleanup dataset submodules. You don't need to schedule
            # auto-import jobs because the user will have switched to the branch to pull it before merging.
            InventoryManager().update_linked_datasets(lb, username)

        return MergeFromBranch(Labbook(id="{}&{}".format(owner, labbook_name),
                                               name=labbook_name, owner=owner))

