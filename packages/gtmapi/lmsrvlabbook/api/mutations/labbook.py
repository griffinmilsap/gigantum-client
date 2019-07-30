# Copyright (c) 2018 FlashX, LLC
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
import base64
import os
import graphene

from gtmcore.container.container import ContainerOperations
from gtmcore.dispatcher import (Dispatcher, jobs)

from gtmcore.inventory.inventory import InventoryManager
from gtmcore.logging import LMLogger
from gtmcore.files import FileOperations
from gtmcore.activity import ActivityStore, ActivityDetailRecord, ActivityDetailType, ActivityRecord, ActivityType
from gtmcore.environment import ComponentManager

from lmsrvcore.api.mutations import ChunkUploadMutation, ChunkUploadInput
from lmsrvcore.auth.user import get_logged_in_username, get_logged_in_author

from lmsrvlabbook.api.connections.labbookfileconnection import LabbookFileConnection
from lmsrvlabbook.api.connections.labbook import LabbookConnection
from lmsrvlabbook.api.objects.labbook import Labbook
from lmsrvlabbook.api.objects.labbookfile import LabbookFile
from lmsrvlabbook.dataloader.labbook import LabBookLoader

logger = LMLogger.get_logger()


class CreateLabbook(graphene.relay.ClientIDMutation):
    """Mutation for creation of a new Labbook on disk"""

    class Input:
        name = graphene.String(required=True)
        description = graphene.String(required=True)
        repository = graphene.String(required=True)
        base_id = graphene.String(required=True)
        revision = graphene.Int(required=True)
        is_untracked = graphene.Boolean(required=False)

    # Return the LabBook instance
    labbook = graphene.Field(lambda: Labbook)

    @classmethod
    def mutate_and_get_payload(cls, root, info, name, description, repository, base_id, revision,
                               is_untracked=False, client_mutation_id=None):
        username = get_logged_in_username()
        inv_manager = InventoryManager()
        lb = inv_manager.create_labbook(username=username,
                                        owner=username,
                                        labbook_name=name,
                                        description=description,
                                        author=get_logged_in_author())

        adr = ActivityDetailRecord(ActivityDetailType.LABBOOK, show=False, importance=0)
        adr.add_value('text/plain', f"Created new LabBook: {username}/{name}")

        # Create activity record
        ar = ActivityRecord(ActivityType.LABBOOK,
                            message=f"Created new LabBook: {username}/{name}",
                            show=True,
                            importance=255,
                            linked_commit=lb.git.commit_hash)
        ar.add_detail_object(adr)

        store = ActivityStore(lb)
        store.create_activity_record(ar)

        cm = ComponentManager(lb)
        cm.add_base(repository, base_id, revision)

        return CreateLabbook(labbook=Labbook(owner=username, name=lb.name))


class DeleteLabbook(graphene.ClientIDMutation):
    """Delete a labbook from disk. """
    class Input:
        owner = graphene.String(required=True)
        labbook_name = graphene.String(required=True)
        confirm = graphene.Boolean(required=True)

    success = graphene.Boolean()

    @classmethod
    def mutate_and_get_payload(cls, root, info, owner, labbook_name, confirm, client_mutation_id=None):
        username = get_logged_in_username()
        lb = InventoryManager().load_labbook(username, owner, labbook_name,
                                             author=get_logged_in_author())
        if confirm:
            logger.info(f"Deleting {str(lb)}...")
            try:
                lb, stopped = ContainerOperations.stop_container(labbook=lb, username=username)
            except OSError as e:
                logger.warning(e)

            lb, docker_removed = ContainerOperations.delete_image(labbook=lb, username=username)
            if not docker_removed:
                raise ValueError(f'Cannot delete docker image for {str(lb)} - unable to delete Project from disk')

            datasets_to_schedule = InventoryManager().delete_labbook(username, owner, labbook_name)

            # Schedule jobs to clean the file cache for any linked datasets (if no other references exist)
            for cleanup_job in datasets_to_schedule:
                # Schedule Job to clear file cache if dataset is no longer in use
                job_metadata = {'method': 'clean_dataset_file_cache'}
                job_kwargs = {
                    'logged_in_username': username,
                    'dataset_owner': cleanup_job.namespace,
                    'dataset_name': cleanup_job.name,
                    'cache_location': cleanup_job.cache_root
                }
                dispatcher = Dispatcher()
                job_key = dispatcher.dispatch_task(jobs.clean_dataset_file_cache, metadata=job_metadata,
                                                   kwargs=job_kwargs)
                logger.info(f"Dispatched clean_dataset_file_cache({ cleanup_job.namespace}/{cleanup_job.name})"
                            f" to Job {job_key}")

            # Verify Delete worked
            if os.path.exists(lb.root_dir):
                logger.error(f'Deleted {str(lb)} but root directory {lb.root_dir} still exists!')
                return DeleteLabbook(success=False)
            else:
                return DeleteLabbook(success=True)
        else:
            logger.info(f"Dry run in deleting {str(lb)} -- not deleted.")
            return DeleteLabbook(success=False)


class ChangeLabbookBase(graphene.relay.ClientIDMutation):
    class Input:
        owner = graphene.String(required=True)
        labbook_name = graphene.String(required=True)
        repository = graphene.String(required=True)
        base_id = graphene.String(required=True)
        revision = graphene.Int(required=True)

    # Return the LabBook instance
    labbook = graphene.Field(lambda: Labbook)

    @classmethod
    def mutate_and_get_payload(cls, root, info, owner, labbook_name, repository, base_id, revision,
                               client_mutation_id=None):
        username = get_logged_in_username()

        lb = InventoryManager().load_labbook(username, owner, labbook_name,
                                             author=get_logged_in_author())

        cm = ComponentManager(lb)
        cm.change_base(repository, base_id, revision)

        return ChangeLabbookBase(labbook=Labbook(owner=owner, name=lb.name))


class SetLabbookDescription(graphene.relay.ClientIDMutation):
    class Input:
        owner = graphene.String(required=True)
        labbook_name = graphene.String(required=True)
        description_content = graphene.String(required=True)

    success = graphene.Boolean()

    @classmethod
    def mutate_and_get_payload(cls, root, info, owner, labbook_name,
                               description_content, client_mutation_id=None):
        username = get_logged_in_username()
        lb = InventoryManager().load_labbook(username, owner, labbook_name,
                                             author=get_logged_in_author())
        lb.description = description_content
        with lb.lock():
            lb.git.add(os.path.join(lb.config_path))
            commit = lb.git.commit('Updating description')

            adr = ActivityDetailRecord(ActivityDetailType.LABBOOK, show=False)
            adr.add_value('text/plain', "Updated description of Project")
            ar = ActivityRecord(ActivityType.LABBOOK,
                                message="Updated description of Project",
                                linked_commit=commit.hexsha,
                                tags=["labbook"],
                                show=False)
            ar.add_detail_object(adr)
            ars = ActivityStore(lb)
            ars.create_activity_record(ar)
        return SetLabbookDescription(success=True)


class CompleteBatchUploadTransaction(graphene.relay.ClientIDMutation):

    class Input:
        owner = graphene.String(required=True)
        labbook_name = graphene.String(required=True)
        transaction_id = graphene.String(required=True)
        cancel = graphene.Boolean()
        rollback = graphene.Boolean()

    success = graphene.Boolean()

    @classmethod
    def mutate_and_get_payload(cls, root, info, owner, labbook_name,
                               transaction_id, cancel=False, rollback=False,
                               client_mutation_id=None):
        username = get_logged_in_username()
        lb = InventoryManager().load_labbook(username, owner, labbook_name,
                                             author=get_logged_in_author())
        with lb.lock():
            FileOperations.complete_batch(lb, transaction_id, cancel=cancel,
                                          rollback=rollback)
        return CompleteBatchUploadTransaction(success=True)


class AddLabbookFile(graphene.relay.ClientIDMutation, ChunkUploadMutation):
    """Mutation to add a file to a labbook. File should be sent in the
    `uploadFile` key as a multi-part/form upload.
    file_path is the relative path from the labbook section specified."""
    class Input:
        owner = graphene.String(required=True)
        labbook_name = graphene.String(required=True)
        section = graphene.String(required=True)
        file_path = graphene.String(required=True)
        chunk_upload_params = ChunkUploadInput(required=True)
        transaction_id = graphene.String(required=True)

    new_labbook_file_edge = graphene.Field(LabbookFileConnection.Edge)

    @classmethod
    def mutate_and_wait_for_chunks(cls, info, **kwargs):
        return AddLabbookFile(new_labbook_file_edge=LabbookFileConnection.Edge(node=None, cursor="null"))

    @classmethod
    def mutate_and_process_upload(cls, info, upload_file_path, upload_filename, **kwargs):
        if not upload_file_path:
            logger.error('No file uploaded')
            raise ValueError('No file uploaded')

        owner = kwargs.get('owner')
        labbook_name = kwargs.get('labbook_name')
        section = kwargs.get('section')
        transaction_id = kwargs.get('transaction_id')
        file_path = kwargs.get('file_path')

        try:
            username = get_logged_in_username()
            lb = InventoryManager().load_labbook(username, owner, labbook_name,
                                                 author=get_logged_in_author())
            dst_path = os.path.join(os.path.dirname(file_path), upload_filename)
            with lb.lock():
                fops = FileOperations.put_file(labbook=lb,
                                               section=section,
                                               src_file=upload_file_path,
                                               dst_path=dst_path,
                                               txid=transaction_id)
        finally:
            try:
                logger.debug(f"Removing temp file {upload_file_path}")
                os.remove(upload_file_path)
            except FileNotFoundError:
                pass

        # Create data to populate edge
        create_data = {'owner': owner,
                       'name': labbook_name,
                       'section': section,
                       'key': fops['key'],
                       '_file_info': fops}

        # TODO: Fix cursor implementation..this currently doesn't make sense when adding edges without a refresh
        cursor = base64.b64encode(f"{0}".encode('utf-8'))
        return AddLabbookFile(new_labbook_file_edge=LabbookFileConnection.Edge(node=LabbookFile(**create_data),
                                                                               cursor=cursor))


class DeleteLabbookFiles(graphene.ClientIDMutation):
    class Input:
        owner = graphene.String(required=True)
        labbook_name = graphene.String(required=True)
        section = graphene.String(required=True)
        file_paths = graphene.List(graphene.String, required=True)

    success = graphene.Boolean()

    @classmethod
    def mutate_and_get_payload(cls, root, info, owner, labbook_name, section, file_paths, client_mutation_id=None):
        username = get_logged_in_username()
        lb = InventoryManager().load_labbook(username, owner, labbook_name,
                                             author=get_logged_in_author())

        with lb.lock():
            FileOperations.delete_files(lb, section, file_paths)

        return DeleteLabbookFiles(success=True)


class MoveLabbookFile(graphene.ClientIDMutation):
    """Method to move/rename a file or directory. If file, both src_path and dst_path should contain the file name.
    If a directory, be sure to include the trailing slash"""
    class Input:
        owner = graphene.String(required=True)
        labbook_name = graphene.String(required=True)
        section = graphene.String(required=True)
        src_path = graphene.String(required=True)
        dst_path = graphene.String(required=True)

    updated_edges = graphene.List(LabbookFileConnection.Edge)

    @classmethod
    def mutate_and_get_payload(cls, root, info, owner, labbook_name, section, src_path, dst_path,
                               client_mutation_id=None, **kwargs):
        username = get_logged_in_username()
        lb = InventoryManager().load_labbook(username, owner, labbook_name,
                                             author=get_logged_in_author())

        with lb.lock():
            mv_results = FileOperations.move_file(lb, section, src_path, dst_path)

        file_edges = list()
        for file_dict in mv_results:
            file_edges.append(LabbookFile(owner=owner,
                                          name=labbook_name,
                                          section=section,
                                          key=file_dict['key'],
                                          is_dir=file_dict['is_dir'],
                                          modified_at=file_dict['modified_at'],
                                          size=str(file_dict['size'])))

        cursors = [base64.b64encode("{}".format(cnt).encode("UTF-8")).decode("UTF-8")
                   for cnt, x in enumerate(file_edges)]

        edge_objs = [LabbookFileConnection.Edge(node=e, cursor=c) for e, c in zip(file_edges, cursors)]

        return MoveLabbookFile(updated_edges=edge_objs)


class MakeLabbookDirectory(graphene.ClientIDMutation):
    class Input:
        owner = graphene.String(required=True)
        labbook_name = graphene.String(required=True)
        section = graphene.String(required=True)
        directory = graphene.String(required=True)

    new_labbook_file_edge = graphene.Field(LabbookFileConnection.Edge)

    @classmethod
    def mutate_and_get_payload(cls, root, info, owner, labbook_name, section, directory,
                               client_mutation_id=None):
        username = get_logged_in_username()
        lb = InventoryManager().load_labbook(username, owner, labbook_name,
                                             author=get_logged_in_author())
        with lb.lock():
            FileOperations.makedir(lb, os.path.join(section, directory), create_activity_record=True)

        # Prime dataloader with labbook you already loaded
        dataloader = LabBookLoader()
        dataloader.prime(f"{owner}&{labbook_name}&{lb.name}", lb)

        # Create data to populate edge
        file_info = FileOperations.get_file_info(lb, section, directory)
        create_data = {'owner': owner,
                       'name': labbook_name,
                       'section': section,
                       'key': file_info['key'],
                       '_file_info': file_info}

        # TODO: Fix cursor implementation, this currently doesn't make sense
        cursor = base64.b64encode(f"{0}".encode('utf-8'))

        return MakeLabbookDirectory(
            new_labbook_file_edge=LabbookFileConnection.Edge(
                node=LabbookFile(**create_data),
                cursor=cursor))


class WriteLabbookReadme(graphene.relay.ClientIDMutation):
    class Input:
        owner = graphene.String(required=True)
        labbook_name = graphene.String(required=True)
        content = graphene.String(required=True)

    updated_labbook = graphene.Field(Labbook)

    @classmethod
    def mutate_and_get_payload(cls, root, info, owner, labbook_name, content, client_mutation_id=None):
        username = get_logged_in_username()
        lb = InventoryManager().load_labbook(username, owner, labbook_name,
                                             author=get_logged_in_author())

        # Write data
        with lb.lock():
            lb.write_readme(content)

        return WriteLabbookReadme(updated_labbook=Labbook(owner=owner, name=labbook_name))


class FetchLabbookEdge(graphene.relay.ClientIDMutation):
    class Input:
        owner = graphene.String(required=True)
        labbook_name = graphene.String(required=True)

    new_labbook_edge = graphene.Field(LabbookConnection.Edge)

    @classmethod
    def mutate_and_get_payload(cls, root, info, owner, labbook_name, client_mutation_id=None):
        username = get_logged_in_username()
        lb = InventoryManager().load_labbook(username, owner, labbook_name,
                                             author=get_logged_in_author())

        cursor = base64.b64encode(f"{0}".encode('utf-8'))
        lbedge = LabbookConnection.Edge(node=Labbook(owner=owner, name=labbook_name),
                                        cursor=cursor)

        return FetchLabbookEdge(new_labbook_edge=lbedge)
