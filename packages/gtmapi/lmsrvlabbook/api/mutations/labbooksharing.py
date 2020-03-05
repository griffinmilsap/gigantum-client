import base64
import graphene
import os
import flask

from gtmcore.activity import ActivityStore, ActivityType, ActivityRecord
from gtmcore.inventory.inventory import InventoryManager
from gtmcore.dispatcher import Dispatcher, jobs
from gtmcore.exceptions import GigantumException
from gtmcore.logging import LMLogger
from gtmcore.workflows import MergeOverride
from gtmcore.workflows.gitlab import GitLabManager, ProjectPermissions

from lmsrvcore.api import logged_mutation
from lmsrvcore.api.mutations import ChunkUploadMutation, ChunkUploadInput
from lmsrvcore.auth.user import get_logged_in_username, get_logged_in_author
from lmsrvcore.utilities import configure_git_credentials

from lmsrvlabbook.api.connections.labbook import LabbookConnection
from lmsrvlabbook.api.objects.labbook import Labbook as LabbookObject

logger = LMLogger.get_logger()


class PublishLabbook(graphene.relay.ClientIDMutation):

    class Input:
        owner = graphene.String(required=True)
        labbook_name = graphene.String(required=True)
        set_public = graphene.Boolean(required=False)

    job_key = graphene.String()

    @classmethod
    @logged_mutation
    def mutate_and_get_payload(cls, root, info, owner, labbook_name, set_public=False,
                               client_mutation_id=None):
        # Load LabBook
        username = get_logged_in_username()
        lb = InventoryManager().load_labbook(username, owner, labbook_name,
                                             author=get_logged_in_author())

        job_metadata = {'method': 'publish_labbook',
                        'labbook': lb.key}
        job_kwargs = {'repository': lb,
                      'username': username,
                      'access_token': flask.g.access_token,
                      'id_token': flask.g.id_token,
                      'public': set_public}
        dispatcher = Dispatcher()
        job_key = dispatcher.dispatch_task(jobs.publish_repository, kwargs=job_kwargs, metadata=job_metadata)
        logger.info(f"Publishing LabBook {lb.root_dir} in background job with key {job_key.key_str}")

        return PublishLabbook(job_key=job_key.key_str)


class SyncLabbook(graphene.relay.ClientIDMutation):

    class Input:
        owner = graphene.String(required=True)
        labbook_name = graphene.String(required=True)
        pull_only = graphene.Boolean(required=False, default=False)
        override_method = graphene.String(default="abort")

    job_key = graphene.String()

    @classmethod
    @logged_mutation
    def mutate_and_get_payload(cls, root, info, owner, labbook_name, pull_only=False,
                               override_method="abort", client_mutation_id=None):
        username = get_logged_in_username()
        lb = InventoryManager().load_labbook(username, owner, labbook_name,
                                             author=get_logged_in_author())

        # Configure git credentials for user
        configure_git_credentials()

        override = MergeOverride(override_method)

        job_metadata = {'method': 'sync_labbook',
                        'labbook': lb.key}
        job_kwargs = {'repository': lb,
                      'pull_only': pull_only,
                      'username': username,
                      'override': override}
        dispatcher = Dispatcher()
        job_key = dispatcher.dispatch_task(jobs.sync_repository, kwargs=job_kwargs, metadata=job_metadata)
        logger.info(f"Syncing LabBook {lb.root_dir} in background job with key {job_key.key_str}")

        return SyncLabbook(job_key=job_key.key_str)


class SetVisibility(graphene.relay.ClientIDMutation):
    class Input:
        owner = graphene.String(required=True)
        labbook_name = graphene.String(required=True)
        visibility = graphene.String(required=True)

    new_labbook_edge = graphene.Field(LabbookConnection.Edge)

    @classmethod
    @logged_mutation
    def mutate_and_get_payload(cls, root, info, owner, labbook_name, visibility,
                               client_mutation_id=None):
        # Load LabBook
        username = get_logged_in_username()
        lb = InventoryManager().load_labbook(username, owner, labbook_name,
                                             author=get_logged_in_author())

        # Configure git creds
        mgr = configure_git_credentials()

        if visibility not in ['public', 'private']:
            raise ValueError(f'Visibility must be either "public" or "private";'
                             f'("{visibility}" invalid)')
        with lb.lock():
            mgr.set_visibility(namespace=owner, repository_name=labbook_name, visibility=visibility)

        cursor = base64.b64encode(f"{0}".encode('utf-8'))
        lb_edge = LabbookConnection.Edge(node=LabbookObject(owner=owner, name=labbook_name),
                                        cursor=cursor)
        return SetVisibility(new_labbook_edge=lb_edge)


class ImportRemoteLabbook(graphene.relay.ClientIDMutation):
    class Input:
        owner = graphene.String(required=True)
        labbook_name = graphene.String(required=True)
        remote_url = graphene.String(required=True)

    job_key = graphene.String()

    @classmethod
    def mutate_and_get_payload(cls, root, info, owner, labbook_name, remote_url, client_mutation_id=None):
        username = get_logged_in_username()
        logger.info(f"Importing remote labbook from {remote_url}")

        # Configure git creds
        configure_git_credentials()

        job_metadata = {'method': 'import_labbook_from_remote'}
        job_kwargs = {
            'remote_url': remote_url,
            'username': username
        }

        dispatcher = Dispatcher()
        job_key = dispatcher.dispatch_task(jobs.import_labbook_from_remote, metadata=job_metadata,
                                           kwargs=job_kwargs)
        logger.info(f"Dispatched import_labbook_from_remote({remote_url}) to Job {job_key}")

        return ImportRemoteLabbook(job_key=job_key.key_str)


class AddLabbookRemote(graphene.relay.ClientIDMutation):
    class Input:
        owner = graphene.String(required=True)
        labbook_name = graphene.String(required=True)
        remote_name = graphene.String(required=True)
        remote_url = graphene.String(required=True)

    success = graphene.Boolean()

    @classmethod
    def mutate_and_get_payload(cls, root, info, owner, labbook_name,
                               remote_name, remote_url,
                               client_mutation_id=None):
        username = get_logged_in_username()
        lb = InventoryManager().load_labbook(username, owner, labbook_name,
                                             author=get_logged_in_author())
        with lb.lock():
            lb.add_remote(remote_name, remote_url)
        return AddLabbookRemote(success=True)


class AddLabbookCollaborator(graphene.relay.ClientIDMutation):
    class Input:
        owner = graphene.String(required=True)
        labbook_name = graphene.String(required=True)
        username = graphene.String(required=True, description="The collaborator username to add")
        permissions = graphene.String(required=True)

    updated_labbook = graphene.Field(LabbookObject)

    @classmethod
    def mutate_and_get_payload(cls, root, info, owner, labbook_name, username, permissions,
                               client_mutation_id=None):
        logged_in_username = get_logged_in_username()
        lb = InventoryManager().load_labbook(logged_in_username, owner, labbook_name,
                                             author=get_logged_in_author())

        if permissions == 'readonly':
            perm = ProjectPermissions.READ_ONLY
            perm_msg = "read-only"
        elif permissions == 'readwrite':
            perm = ProjectPermissions.READ_WRITE
            perm_msg = "read & write"
        elif permissions == 'owner':
            perm = ProjectPermissions.OWNER
            perm_msg = "administrator"
        else:
            raise ValueError(f"Unknown permission set: {permissions}")

        # Configure git creds
        mgr = configure_git_credentials()
        existing_collabs = mgr.get_collaborators(owner, labbook_name)

        # Add / Update collaborator
        if username not in [n[1] for n in existing_collabs]:
            collaborator_msg = f"Adding collaborator {username} with {perm_msg} permissions"
            logger.info(f"Adding user {username} to {owner}/{labbook_name}"
                        f"with permission {perm}")
            mgr.add_collaborator(owner, labbook_name, username, perm)
        else:
            collaborator_msg = f"Updating collaborator {username} to {perm_msg} permissions"
            logger.warning(f"Changing permission of {username} on"
                           f"{owner}/{labbook_name} to {perm}")
            mgr.delete_collaborator(owner, labbook_name, username)
            mgr.add_collaborator(owner, labbook_name, username, perm)

        # Add to activity feed
        store = ActivityStore(lb)
        ar = ActivityRecord(ActivityType.LABBOOK,
                            message=collaborator_msg,
                            linked_commit="no-linked-commit",
                            importance=255)
        store.create_activity_record(ar)

        # Return response
        create_data = {"owner": owner,
                       "name": labbook_name}

        return AddLabbookCollaborator(updated_labbook=LabbookObject(**create_data))


class DeleteLabbookCollaborator(graphene.relay.ClientIDMutation):
    class Input:
        owner = graphene.String(required=True)
        labbook_name = graphene.String(required=True)
        username = graphene.String(required=True, description="Collaborator username to remove.")

    updated_labbook = graphene.Field(LabbookObject)

    @classmethod
    def mutate_and_get_payload(cls, root, info, owner, labbook_name, username, client_mutation_id=None):
        # Configure git creds
        mgr = configure_git_credentials()
        mgr.delete_collaborator(owner, labbook_name, username)

        # Add to activity feed
        logged_in_username = get_logged_in_username()
        lb = InventoryManager().load_labbook(logged_in_username, owner, labbook_name,
                                             author=get_logged_in_author())
        store = ActivityStore(lb)
        ar = ActivityRecord(ActivityType.LABBOOK,
                            message=f"Removing collaborator {username}",
                            linked_commit="no-linked-commit",
                            importance=255)
        store.create_activity_record(ar)

        # Return response
        create_data = {"owner": owner,
                       "name": labbook_name}

        return DeleteLabbookCollaborator(updated_labbook=LabbookObject(**create_data))


class DeleteRemoteLabbook(graphene.ClientIDMutation):
    """Delete a labbook from the remote repository."""
    class Input:
        owner = graphene.String(required=True)
        labbook_name = graphene.String(required=True)
        confirm = graphene.Boolean(required=True)

    success = graphene.Boolean()

    @classmethod
    def mutate_and_get_payload(cls, root, info, owner, labbook_name, confirm, client_mutation_id=None):
        if confirm is True:
            # Extract valid Bearer and ID tokens
            access_token = flask.g.get('access_token', None)
            id_token = flask.g.get('id_token', None)
            if not access_token or not id_token:
                raise ValueError("A valid session is required for this operation and tokens are missing.")

            # Get remote server configuration
            config = flask.current_app.config['LABMGR_CONFIG']
            remote_config = config.get_remote_configuration()

            # Perform delete operation
            mgr = GitLabManager(remote_config['git_remote'],
                                remote_config['hub_api'],
                                access_token=access_token,
                                id_token=id_token)
            mgr.remove_repository(owner, labbook_name)
            logger.info(f"Deleted {owner}/{labbook_name} from the remote repository {remote_config['git_remote']}")

            # Remove locally any references to that cloud repo that's just been deleted.
            try:
                username = get_logged_in_username()
                lb = InventoryManager().load_labbook(username, owner, labbook_name,
                                                     author=get_logged_in_author())
                lb.remove_remote()
                lb.remove_lfs_remotes()
            except GigantumException as e:
                logger.warning(e)

            return DeleteRemoteLabbook(success=True)
        else:
            logger.info(f"Dry run deleting {labbook_name} from remote repository -- not deleted.")
            return DeleteRemoteLabbook(success=False)


class ExportLabbook(graphene.relay.ClientIDMutation):
    class Input:
        owner = graphene.String(required=True)
        labbook_name = graphene.String(required=True)

    job_key = graphene.String()

    @classmethod
    def mutate_and_get_payload(cls, root, info, owner, labbook_name, client_mutation_id=None):
        username = get_logged_in_username()
        config = flask.current_app.config['LABMGR_CONFIG']
        working_directory = config.config['git']['working_directory']
        lb = InventoryManager().load_labbook(username, owner, labbook_name,
                                             author=get_logged_in_author())

        job_metadata = {'method': 'export_labbook_as_zip',
                        'labbook': lb.key}
        job_kwargs = {'labbook_path': lb.root_dir,
                      'lb_export_directory': os.path.join(working_directory, 'export')}
        dispatcher = Dispatcher()
        job_key = dispatcher.dispatch_task(jobs.export_labbook_as_zip,
                                           kwargs=job_kwargs,
                                           metadata=job_metadata)

        return ExportLabbook(job_key=job_key.key_str)


class ImportLabbook(graphene.relay.ClientIDMutation, ChunkUploadMutation):
    class Input:
        chunk_upload_params = ChunkUploadInput(required=True)

    import_job_key = graphene.String()

    @classmethod
    def mutate_and_wait_for_chunks(cls, info, **kwargs):
        return ImportLabbook()

    @classmethod
    def mutate_and_process_upload(cls, info, upload_file_path, upload_filename, **kwargs):
        if not upload_file_path:
            logger.error('No file uploaded')
            raise ValueError('No file uploaded')

        username = get_logged_in_username()
        job_metadata = {'method': 'import_labbook_from_zip'}
        job_kwargs = {
            'archive_path': upload_file_path,
            'username': username,
            'owner': username
        }
        dispatcher = Dispatcher()
        job_key = dispatcher.dispatch_task(jobs.import_labboook_from_zip,
                                           kwargs=job_kwargs,
                                           metadata=job_metadata)

        return ImportLabbook(import_job_key=job_key.key_str)
