import graphene

from gtmcore.labbook import SecretStore
from gtmcore.inventory.inventory import InventoryManager
from gtmcore.logging import LMLogger
from gtmcore.activity import ActivityStore, ActivityDetailRecord, ActivityDetailType, \
    ActivityRecord, ActivityType, ActivityAction
from gtmcore.activity.utils import ImmutableDict, TextData, DetailRecordList, ImmutableList

from lmsrvcore.auth.user import get_logged_in_username, get_logged_in_author
from lmsrvlabbook.api.objects.environment import Environment
from lmsrvcore.api.mutations import ChunkUploadMutation, ChunkUploadInput

logger = LMLogger.get_logger()


class InsertSecretsEntry(graphene.relay.ClientIDMutation):
    """ Creates an entry in the Project's Secret Store. Note, you will
    need to use the Upload mutation to actually put the file content in
    the secret store. """
    class Input:
        owner = graphene.String(required=True)
        labbook_name = graphene.String(required=True)
        filename = graphene.String(required=True, description="Filename (not a full path) of the secrets file.")
        mount_path = graphene.String(required=True, description="Path to directory INSIDE the container")

    environment = graphene.Field(lambda: Environment)

    @classmethod
    def mutate_and_get_payload(cls, root, info, owner, labbook_name, filename,
                               mount_path, client_mutation_id=None):

        if len(mount_path) > 0 and mount_path[0] == '~':
            mount_path = mount_path.replace('~', '/home/giguser')

        if not cls._is_target_valid(mount_path):
            raise ValueError(f"Mount path {mount_path} is not a valid path")

        username = get_logged_in_username()
        lb = InventoryManager().load_labbook(username, owner, labbook_name,
                                             author=get_logged_in_author())
        with lb.lock():
            secstore = SecretStore(lb, username)
            secstore[filename] = mount_path
            cls._record_insert_activity(secstore, filename, lb, mount_path)

        env = Environment(owner=owner, name=lb.name)
        return InsertSecretsEntry(environment=env)

    @classmethod
    def _is_target_valid(cls, target_path) -> bool:
        """Return False if the given target_path contains invalid sequences. """
        bad_tokens = ["..", "~", "/mnt", "/etc"]
        return all([b not in target_path for b in bad_tokens])

    @classmethod
    def _record_insert_activity(cls, secret_store, filename, lb, mount_path):
        """Make an activity record for the insertion of the secret. """
        lb.git.add(secret_store.secret_path)
        lb.git.commit("Updated secrets registry.")
        commit = lb.git.commit_hash
        adr = ActivityDetailRecord(ActivityDetailType.LABBOOK,
                                   show=True,
                                   action=ActivityAction.CREATE,
                                   data=TextData('markdown',
                                                 f"Created new entry for secrets file {filename}"
                                                 f"to map to {mount_path}"))

        ar = ActivityRecord(ActivityType.LABBOOK,
                            message=f"Created entry for secrets file {filename}",
                            linked_commit=commit,
                            tags=ImmutableList(["labbook", "secrets"]),
                            show=True,
                            detail_objects=DetailRecordList([adr]))

        ars = ActivityStore(lb)
        ars.create_activity_record(ar)


class RemoveSecretsEntry(graphene.relay.ClientIDMutation):
    """ Removes the entry from the Project's SecretStore. Will also remove
    any associated files. This undoes the InsertSecretsEntry mutation. """
    class Input:
        owner = graphene.String(required=True)
        labbook_name = graphene.String(required=True)
        filename = graphene.String(required=True, description="Filename of secret to remove from the registry")

    environment = graphene.Field(lambda: Environment)

    @classmethod
    def mutate_and_get_payload(cls, root, info, owner, labbook_name, filename,
                               client_mutation_id=None):
        username = get_logged_in_username()
        lb = InventoryManager().load_labbook(username, owner, labbook_name,
                                             author=get_logged_in_author())
        with lb.lock():
            secret_store = SecretStore(lb, username)
            del secret_store[filename]
            cls._record_remove_activity(secret_store, filename, lb)

        env = Environment(owner=owner, name=lb.name)
        return InsertSecretsEntry(environment=env)

    @classmethod
    def _record_remove_activity(cls, secret_store, filename, lb):
        """Make an activity record for the removal of the secret. """
        lb.git.add(secret_store.secret_path)
        lb.git.commit("Removed entry from secrets registry.")
        commit = lb.git.commit_hash
        adr = ActivityDetailRecord(ActivityDetailType.LABBOOK,
                                   show=True,
                                   action=ActivityAction.DELETE,
                                   data=TextData('markdown',
                                                 f"Removed entry for secrets file {filename}"))

        ar = ActivityRecord(ActivityType.LABBOOK,
                            message=f"Removed entry for secrets file {filename}",
                            linked_commit=commit,
                            tags=ImmutableList(["labbook", "secrets"]),
                            show=True,
                            detail_objects=DetailRecordList([adr]))

        ars = ActivityStore(lb)
        ars.create_activity_record(ar)


class UploadSecretsFile(graphene.relay.ClientIDMutation, ChunkUploadMutation):
    """Uploades the actual secrets file pertaining to the given filename in the
    SecretStore registry. The InsertSecretsEntry must be called first. """
    class Input:
        owner = graphene.String(required=True)
        labbook_name = graphene.String(required=True)
        chunk_upload_params = ChunkUploadInput(required=True)
        transaction_id = graphene.String(required=True)

    environment = graphene.Field(lambda: Environment)

    @classmethod
    def mutate_and_wait_for_chunks(cls, info, **kwargs):
        return UploadSecretsFile(environment=None)

    @classmethod
    def mutate_and_process_upload(cls, info, upload_file_path, upload_filename, **kwargs):
        if not upload_file_path:
            logger.error('No file uploaded')
            raise ValueError('No file uploaded')

        username = get_logged_in_username()
        owner = kwargs.get('owner')
        labbook_name = kwargs.get('labbook_name')

        lb = InventoryManager().load_labbook(username, owner, labbook_name)
        with lb.lock():
            secret_store = SecretStore(lb, username)
            inserted_path = secret_store.insert_file(upload_file_path,
                                                     dst_filename=upload_filename)

        env = Environment(owner=owner, name=lb.name)
        return UploadSecretsFile(environment=env)


class DeleteSecretsFile(graphene.ClientIDMutation):
    """Delete the secrets file on the host, but without removing the
    corresponding entry in the registry. """
    class Input:
        owner = graphene.String(required=True)
        labbook_name = graphene.String(required=True)
        filename = graphene.String(required=True, description="Filename of secrets file to delete from the host "
                                                              "- does NOT delete from the registry")

    environment = graphene.Field(lambda: Environment)

    @classmethod
    def mutate_and_get_payload(cls, root, info, owner, labbook_name, filename,
                               client_mutation_id=None):
        username = get_logged_in_username()
        lb = InventoryManager().load_labbook(username, owner, labbook_name,
                                             author=get_logged_in_author())
        with lb.lock():
            secstore = SecretStore(lb, username)
            secstore.delete_file(filename)

        env = Environment(owner=owner, name=lb.name)
        return DeleteSecretsFile(environment=env)
