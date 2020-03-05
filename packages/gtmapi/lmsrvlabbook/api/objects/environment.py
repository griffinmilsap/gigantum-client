import graphene
import base64

from gtmcore.dispatcher import Dispatcher
from gtmcore.labbook import SecretStore
from gtmcore.environment.componentmanager import ComponentManager
from gtmcore.container import container_for_context
from gtmcore.logging import LMLogger
from gtmcore.environment.bundledapp import BundledAppManager

from lmsrvcore.api.interfaces import GitRepository
from lmsrvcore.auth.user import get_logged_in_username
from lmsrvcore.api.connections import ListBasedConnection

from lmsrvlabbook.api.connections.environment import PackageComponentConnection
from lmsrvlabbook.api.connections.secrets import SecretFileMappingConnection
from lmsrvlabbook.api.objects.basecomponent import BaseComponent
from lmsrvlabbook.api.objects.packagecomponent import PackageComponent
from lmsrvlabbook.api.objects.secrets import SecretFileMapping
from lmsrvlabbook.api.objects.bundledapp import BundledApp
from lmsrvlabbook.dataloader.package import PackageDataloader

logger = LMLogger.get_logger()


class ImageStatus(graphene.Enum):
    """An enumeration for Docker image status"""

    # The image has not be built locally yet
    DOES_NOT_EXIST = 0

    # The image is being built
    BUILD_IN_PROGRESS = 1

    # The task to build the image is stuck in queued
    BUILD_QUEUED = 99

    # The image has been built and the Dockerfile has yet to change
    EXISTS = 2

    # The image has been built and the Dockerfile has been edited
    STALE = 3

    # The image failed to build
    BUILD_FAILED = 4


class ContainerStatus(graphene.Enum):
    """An enumeration for container image status"""

    # The container is not running
    NOT_RUNNING = 0

    # The container is starting
    STARTING = 1

    # The container is running
    RUNNING = 2


class Environment(graphene.ObjectType):
    """A type that represents the Environment for a LabBook"""
    class Meta:
        interfaces = (graphene.relay.Node, GitRepository)

    _base_component_data = None

    # The name of the current branch
    image_status = graphene.Field(ImageStatus)

    # Run state
    container_status = graphene.Field(ContainerStatus)

    # The LabBook's Base Component
    base = graphene.Field(BaseComponent)

    # The LabBook's Base Component's latest revision
    base_latest_revision = graphene.Int()

    # The LabBook's Package manager installed dependencies
    package_dependencies = graphene.ConnectionField(PackageComponentConnection)

    # A custom docker snippet to be run after all other dependencies and bases have been added.
    docker_snippet = graphene.String()

    # A mapping that enumerates where secrets files should be mapped into the Project container.
    secrets_file_mapping = graphene.ConnectionField(SecretFileMappingConnection)

    # A list of bundled apps
    bundled_apps = graphene.List(BundledApp)


    @classmethod
    def get_node(cls, info, id):
        """Method to resolve the object based on it's Node ID"""
        # Parse the key
        owner, name = id.split("&")

        return Environment(id=f"{owner}&{name}", name=name, owner=owner)

    def resolve_id(self, info):
        """Resolve the unique Node id for this object"""
        if not self.owner or not self.name:
            raise ValueError("Resolving a Environment Node ID requires owner and name to be set")

        return f"{self.owner}&{self.name}"

    def helper_resolve_image_status(self, labbook):
        """Helper to resolve the image status of a labbook"""

        dispatcher = Dispatcher()
        lb_jobs = [dispatcher.query_task(j.job_key) for j in dispatcher.get_jobs_for_labbook(labbook.key)]

        for j in lb_jobs:
            logger.debug("Current job for labbook: status {}, meta {}".format(j.status, j.meta))

        # First, check if image exists or not -- The first step of building an image untags any existing ones.
        # Therefore, we know that if one exists, there most likely is not one being built.
        labbook_container = container_for_context(username=get_logged_in_username(), labbook=labbook)

        if labbook_container.image_available():
            image_status = ImageStatus.EXISTS
        else:
            image_status = ImageStatus.DOES_NOT_EXIST

        if any([j.status == 'failed' and j.meta.get('method') == 'build_image' for j in lb_jobs]):
            logger.debug("Image status for {} is BUILD_FAILED".format(labbook.key))
            if image_status == ImageStatus.EXISTS:
                # The indication that there's a failed job is probably lingering from a while back, so don't
                # change the status to FAILED. Only do that if there is no Docker image.
                logger.debug(f'Got failed build_image for labbook {labbook.key}, but image exists.')
            else:
                image_status = ImageStatus.BUILD_FAILED

        if any([j.status in ['started'] and j.meta.get('method') == 'build_image' for j in lb_jobs]):
            logger.debug(f"Image status for {labbook.key} is BUILD_IN_PROGRESS")
            # build_image being in progress takes precedence over if image already exists (unlikely event).
            if image_status == ImageStatus.EXISTS:
                logger.warning(f'Got build_image for labbook {labbook.key}, but image exists.')
            image_status = ImageStatus.BUILD_IN_PROGRESS

        if any([j.status in ['queued'] and j.meta.get('method') == 'build_image' for j in lb_jobs]):
            logger.warning(f"build_image for {labbook.key} stuck in queued state")
            image_status = ImageStatus.BUILD_QUEUED

        return image_status.value

    def resolve_image_status(self, info):
        """Resolve the image_status field"""
        return info.context.labbook_loader.load(f"{get_logged_in_username()}&{self.owner}&{self.name}").then(
            lambda labbook: self.helper_resolve_image_status(labbook))

    def helper_resolve_container_status(self, labbook):
        """Helper to resolve the container status of a labbook"""
        container_ops = container_for_context(get_logged_in_username(), labbook=labbook)
        container_name = container_ops.default_image_tag(self.owner, self.name)

        status = container_ops.query_container(container_name)

        if status == 'running':
            container_status = ContainerStatus.RUNNING
        else:
            container_status = ContainerStatus.NOT_RUNNING

        return container_status.value

    def resolve_container_status(self, info):
        """Resolve the container_status field"""
        return info.context.labbook_loader.load(f"{get_logged_in_username()}&{self.owner}&{self.name}").then(
            lambda labbook: self.helper_resolve_container_status(labbook))

    def helper_resolve_base(self, labbook):
        """Helper to resolve the base component object"""
        # Get base image data from the LabBook
        if not self._base_component_data:
            cm = ComponentManager(labbook)
            self._base_component_data = cm.base_fields

        return BaseComponent(id=f"{self._base_component_data['repository']}&{self._base_component_data['id']}&"
                                f"{self._base_component_data['revision']}",
                             repository=self._base_component_data['repository'],
                             component_id=self._base_component_data['id'],
                             revision=int(self._base_component_data['revision']),
                             _component_data=self._base_component_data)

    def resolve_base(self, info):
        """Method to get the LabBook's base component

        Args:
            info:

        Returns:

        """
        return info.context.labbook_loader.load(f"{get_logged_in_username()}&{self.owner}&{self.name}").then(
            lambda labbook: self.helper_resolve_base(labbook))

    def helper_resolve_base_latest_revision(self, labbook) -> int:
        """Helper to resolve the base component's latest revision"""
        cm = ComponentManager(labbook)
        if not self._base_component_data:
            self._base_component_data = cm.base_fields

        available_bases = cm.bases.get_base_versions(self._base_component_data['repository'],
                                                     self._base_component_data['id'])
        # The first item in the available bases list is the latest base. This is a list of tuples (revision, base data)
        latest_revision, _ = available_bases[0]
        return int(latest_revision)

    def resolve_base_latest_revision(self, info):
        """Method to get the LabBook's base component's latest revision

        Args:
            info:

        Returns:

        """
        return info.context.labbook_loader.load(f"{get_logged_in_username()}&{self.owner}&{self.name}").then(
            lambda labbook: self.helper_resolve_base_latest_revision(labbook))

    @staticmethod
    def helper_resolve_package_dependencies(labbook, kwargs):
        """Helper to resolve the packages"""
        cm = ComponentManager(labbook)
        edges = cm.get_component_list("package_manager")

        if edges:
            cursors = [base64.b64encode("{}".format(cnt).encode("UTF-8")).decode("UTF-8") for cnt, x in
                       enumerate(edges)]

            # Process slicing and cursor args
            lbc = ListBasedConnection(edges, cursors, kwargs)
            lbc.apply()

            # Create dataloader
            keys = [f"{k['manager']}&{k['package']}" for k in lbc.edges]
            vd = PackageDataloader(keys, labbook, get_logged_in_username())

            # Get DevEnv instances
            edge_objs = []
            for edge, cursor in zip(lbc.edges, lbc.cursors):
                edge_objs.append(PackageComponentConnection.Edge(node=PackageComponent(_dataloader=vd,
                                                                                       manager=edge['manager'],
                                                                                       package=edge['package'],
                                                                                       version=edge['version'],
                                                                                       from_base=edge['from_base'],
                                                                                       is_valid=True,
                                                                                       schema=edge['schema']),
                                                                 cursor=cursor))

            return PackageComponentConnection(edges=edge_objs, page_info=lbc.page_info)

        else:
            return PackageComponentConnection(edges=[], page_info=graphene.relay.PageInfo(has_next_page=False,
                                                                                          has_previous_page=False))

    def resolve_package_dependencies(self, info, **kwargs):
        """Method to get the LabBook's package manager dependencies

        Args:
            info:

        Returns:

        """
        return info.context.labbook_loader.load(f"{get_logged_in_username()}&{self.owner}&{self.name}").then(
            lambda labbook: self.helper_resolve_package_dependencies(labbook, kwargs))

    @staticmethod
    def helper_resolve_docker_snippet(labbook):
        """Helper to get custom docker snippet"""
        cm = ComponentManager(labbook)
        docker_components = cm.get_component_list('docker')
        if len(docker_components) == 1:
            return '\n'.join(docker_components[0]['content'])
        elif len(docker_components) > 1:
            raise ValueError('There should only be one custdom docker component')
        else:
            return ""

    def resolve_docker_snippet(self, info):
        """Method to resolve  the docker snippet for this labbook. Right now only 1 snippet is supported"""
        return info.context.labbook_loader.load(f"{get_logged_in_username()}&{self.owner}&{self.name}").then(
            lambda labbook: self.helper_resolve_docker_snippet(labbook))

    @staticmethod
    def helper_resolve_secrets_file_mapping(labbook, kwargs):
        secrets_store = SecretStore(labbook, get_logged_in_username())
        edges = secrets_store.secret_map.keys()

        if edges:
            cursors = [base64.b64encode("{}".format(cnt).encode("UTF-8")).decode("UTF-8")
                       for cnt, x in enumerate(edges)]

            # Process slicing and cursor args
            lbc = ListBasedConnection(edges, cursors, kwargs)
            lbc.apply()

            # Get DevEnv instances
            edge_objs = []
            for edge, cursor in zip(lbc.edges, lbc.cursors):
                node_obj = SecretFileMapping(owner=labbook.owner, name=labbook.name,
                                             filename=edge, mount_path=secrets_store[edge])
                edge_objs.append(SecretFileMappingConnection.Edge(node=node_obj, cursor=cursor))
            return SecretFileMappingConnection(edges=edge_objs, page_info=lbc.page_info)

        else:
            pi = graphene.relay.PageInfo(has_next_page=False, has_previous_page=False)
            return SecretFileMappingConnection(edges=[], page_info=pi)

    def resolve_secrets_file_mapping(self, info, **kwargs):
        return info.context.labbook_loader.load(f"{get_logged_in_username()}&{self.owner}&{self.name}").then(
            lambda labbook: self.helper_resolve_secrets_file_mapping(labbook, kwargs))

    def helper_resolve_bundled_apps(self, labbook):
        """Helper to get list of BundledApp objects"""
        bam = BundledAppManager(labbook)
        apps = bam.get_bundled_apps()
        return [BundledApp(name=self.name, owner=self.owner, app_name=x) for x in apps]

    def resolve_bundled_apps(self, info):
        """Method to resolve  the bundled apps for this labbook"""
        return info.context.labbook_loader.load(f"{get_logged_in_username()}&{self.owner}&{self.name}").then(
            lambda labbook: self.helper_resolve_bundled_apps(labbook))
