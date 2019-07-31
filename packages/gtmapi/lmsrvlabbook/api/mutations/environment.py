import os
import graphene
import confhttpproxy

from gtmcore.configuration import get_docker_client
from gtmcore.imagebuilder import ImageBuilder
from gtmcore.dispatcher import Dispatcher, jobs

from gtmcore.labbook import SecretStore, LabBook
from gtmcore.inventory.inventory import InventoryManager
from gtmcore.container.container import ContainerOperations
from gtmcore.mitmproxy.mitmproxy import MITMProxyOperations
from gtmcore.container.utils import infer_docker_image_name
from gtmcore.workflows import LabbookWorkflow, ContainerWorkflows
from gtmcore.logging import LMLogger
from gtmcore.activity import ActivityAction, ActivityDetailRecord, ActivityDetailType, ActivityRecord, ActivityStore, ActivityType
from gtmcore.activity.services import stop_labbook_monitor

from lmsrvcore.auth.user import get_logged_in_username, get_logged_in_author
from lmsrvlabbook.api.objects.environment import Environment
from lmsrvcore.api.mutations import ChunkUploadMutation, ChunkUploadInput

logger = LMLogger.get_logger()


class CancelBuild(graphene.relay.ClientIDMutation):
    class Input:
        owner = graphene.String(required=True)
        labbook_name = graphene.String(required=True)

    build_stopped = graphene.Boolean()
    message = graphene.String()

    @classmethod
    def mutate_and_get_payload(cls, root, info, owner, labbook_name,
                               client_mutation_id=None):
        username = get_logged_in_username()
        lb = InventoryManager().load_labbook(username, owner, labbook_name)
        d = Dispatcher()
        lb_jobs = d.get_jobs_for_labbook(lb.key)

        jobs = [j for j in d.get_jobs_for_labbook(lb.key)
                if j.meta.get('method') == 'build_image'
                and j.status == 'started']

        if len(jobs) == 1:
            d.abort_task(jobs[0].job_key)
            ContainerOperations.delete_image(lb, username=username)
            return CancelBuild(build_stopped=True, message="Stopped build")
        elif len(jobs) == 0:
            logger.warning(f"No build_image tasks found for {str(lb)}")
            return CancelBuild(build_stopped=False, message="No build task found")
        else:
            logger.warning(f"Multiple build jobs found for {str(lb)}")
            return CancelBuild(build_stopped=False, message="Multiple builds found")


class BuildImage(graphene.relay.ClientIDMutation):
    """Mutator to build a LabBook's Docker Image"""

    class Input:
        owner = graphene.String(required=True)
        labbook_name = graphene.String(required=True)
        no_cache = graphene.Boolean(required=False)

    # Return the Environment instance
    environment = graphene.Field(lambda: Environment)

    # The background job key, this may be None
    background_job_key = graphene.String()

    @staticmethod
    def get_container_status(labbook_name: str, owner: str, username: str) -> bool:
        labbook_key = infer_docker_image_name(labbook_name=labbook_name, owner=owner,
                                              username=username)
        try:
            client = get_docker_client()
            container = client.containers.get(labbook_key)
            if container.status == "running":
                return True
            else:
                return False
        except:
            pass

        return False

    @classmethod
    def mutate_and_get_payload(cls, root, info, owner, labbook_name, no_cache=False, client_mutation_id=None):
        username = get_logged_in_username()

        if BuildImage.get_container_status(labbook_name, owner, username):
            raise ValueError(f'Cannot build image for running container {owner}/{labbook_name}')

        lb = InventoryManager().load_labbook(username, owner, labbook_name,
                                             author=get_logged_in_author())

        # Generate Dockerfile
        # TODO BVB - Move to build_image ??
        ib = ImageBuilder(lb)
        ib.assemble_dockerfile(write=True)

        # Kick off building in a background thread
        d = Dispatcher()
        build_kwargs = {
            'path': lb.root_dir,
            'username': username,
            'nocache': no_cache
        }

        metadata = {'labbook': lb.key,
                    'method': 'build_image'}

        res = d.dispatch_task(jobs.build_labbook_image, kwargs=build_kwargs, metadata=metadata)

        return BuildImage(environment=Environment(owner=owner, name=labbook_name),
                          background_job_key=res.key_str)


class StartContainer(graphene.relay.ClientIDMutation):
    """Mutator to start a LabBook's Docker Image in a container"""

    class Input:
        owner = graphene.String(required=True)
        labbook_name = graphene.String(required=True)

    # Return the Environment instance
    environment = graphene.Field(lambda: Environment)

    @classmethod
    def mutate_and_get_payload(cls, root, info, owner, labbook_name, client_mutation_id=None):
        username = get_logged_in_username()
        lb = InventoryManager().load_labbook(username, owner, labbook_name,
                                             author=get_logged_in_author())

        with lb.lock():
            container_id = ContainerWorkflows.start_labbook(lb, username)
        logger.info(f'Started new {lb} container ({container_id})')

        return StartContainer(environment=Environment(owner=owner, name=labbook_name))


class StopContainer(graphene.relay.ClientIDMutation):
    """Mutation to stop a Docker container. """

    class Input:
        owner = graphene.String(required=True)
        labbook_name = graphene.String(required=True)

    # Return the Environment instance
    environment = graphene.Field(lambda: Environment)

    @classmethod
    def _stop_container(cls, lb, username):
        """Stop container and also do necessary cleanup of confhttpproxy, monitors, etc.

        Currently, this supports two cases, applications monitored by MITMProxy,
        and Jupyter. So, for now, if we can't find an mitmproxy endpoint, we assume
        we're dealing with a jupyter container.
        """

        pr = confhttpproxy.ProxyRouter.get_proxy(lb.client_config.config['proxy'])

        # Remove route from proxy
        lb_name = ContainerOperations.labbook_image_name(lb, username)
        if MITMProxyOperations.get_mitmendpoint(lb_name):
            # there is an MITMProxy (currently only used for RStudio)
            proxy_endpoint = MITMProxyOperations.stop_mitm_proxy(lb_name)
            tool = 'rserver'
        else:
            lb_ip = ContainerOperations.get_labbook_ip(lb, username)
            # The only alternative to mitmproxy (currently) is jupyter
            # TODO in #453: Construction of this URL should be encapsulated in Jupyter Dev Tool logic
            proxy_endpoint = f'http://{lb_ip}:8888'
            tool = 'jupyter'

        est_target = pr.get_matching_routes(proxy_endpoint, tool)

        for i, target in enumerate(est_target):
            if i == 1:
                # We have > 1 entry in the router, which shouldn't happen
                logger.warning(f'Removing multiple routes for {tool} on {proxy_endpoint} during Project container stop.')
            pr.remove(target[1:])

        wf = LabbookWorkflow(lb)
        wf.garbagecollect()

        # Clean up empty bind mount dirs from datasets if needed
        submodules = lb.git.list_submodules()
        for submodule in submodules:
            namespace, dataset_name = submodule['name'].split("&")
            bind_location = os.path.join(lb.root_dir, 'input', dataset_name)
            if os.path.isdir(bind_location):
                os.rmdir(bind_location)

        # stop labbook monitor - but do not prevent stopping the Docker container if it fails.
        try:
            stop_labbook_monitor(lb, username)
        except Exception as e:
            logger.error(f"Cannot stop monitor for {str(lb)}: {e}")

        lb, stopped = ContainerOperations.stop_container(labbook=lb, username=username)

        if not stopped:
            # TODO DK: Why would stopped=False? Should this move up??
            raise ValueError(f"Failed to stop labbook {lb.name}")

    @classmethod
    def mutate_and_get_payload(cls, root, info, owner, labbook_name, client_mutation_id=None):
        username = get_logged_in_username()
        lb = InventoryManager().load_labbook(username, owner, labbook_name,
                                             author=get_logged_in_author())

        with lb.lock():
            cls._stop_container(lb, username)

        return StopContainer(environment=Environment(owner=owner, name=labbook_name))
