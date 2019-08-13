import graphene
import base64
import flask
from gtmcore.activity import ActivityStore

from lmsrvcore.caching import DatasetCacheController
from lmsrvcore.auth.identity import parse_token
from lmsrvcore.auth.user import get_logged_in_username
from lmsrvcore.api.interfaces import GitRepository

from gtmcore.dataset.manifest import Manifest
from gtmcore.workflows.gitlab import GitLabManager, ProjectPermissions, GitLabException
from gtmcore.inventory.inventory import InventoryManager
from gtmcore.logging import LMLogger
from gtmcore.inventory.branching import BranchManager

from lmsrvlabbook.api.objects.datasettype import DatasetType
from lmsrvlabbook.api.objects.collaborator import Collaborator
from lmsrvlabbook.api.connections.activity import ActivityConnection
from lmsrvlabbook.api.objects.activity import ActivityDetailObject, ActivityRecordObject
from lmsrvlabbook.api.connections.datasetfile import DatasetFileConnection, DatasetFile
from lmsrvlabbook.api.objects.overview import DatasetOverview

logger = LMLogger.get_logger()


class DatasetConfigurationParameter(graphene.ObjectType):
    """A simple type that represents a Dataset configuration parameter from a storage backend class"""
    parameter = graphene.String()
    description = graphene.String()
    parameter_type = graphene.String()
    value = graphene.String()


class DatasetConfigurationParameterInput(graphene.InputObjectType):
    parameter = graphene.String(required=True)
    parameter_type = graphene.String(required=True)
    value = graphene.String(required=True)


class Dataset(graphene.ObjectType, interfaces=(graphene.relay.Node, GitRepository)):
    """A type representing a Dataset and all of its contents

    Datasets are uniquely identified by both the "owner" and the "name" of the Dataset

    """
    # Store collaborator data so it is only fetched once per request
    _collaborators = None

    # A short description of the dataset limited to 140 UTF-8 characters
    description = graphene.String()

    # The DatasetType for this dataset
    dataset_type = graphene.Field(DatasetType)

    # Data schema version of this dataset. It may be behind the most recent version and need
    # to be upgraded.
    schema_version = graphene.Int()

    # Creation date/timestamp in UTC in ISO format
    created_on_utc = graphene.types.datetime.DateTime()

    # List of collaborators
    collaborators = graphene.List(Collaborator)

    # A boolean indicating if the current user can manage collaborators
    can_manage_collaborators = graphene.Boolean()

    # Last modified date/timestamp in UTC in ISO format
    modified_on_utc = graphene.types.datetime.DateTime()

    # Connection to Activity Entries
    activity_records = graphene.relay.ConnectionField(ActivityConnection)

    # List of all files and directories within the section
    all_files = graphene.relay.ConnectionField(DatasetFileConnection)

    # Access a detail record directly, which is useful when fetching detail items
    detail_record = graphene.Field(ActivityDetailObject, key=graphene.String())
    detail_records = graphene.List(ActivityDetailObject, keys=graphene.List(graphene.String))

    visibility = graphene.String()

    # Get the URL of the remote origin
    default_remote = graphene.String()

    # Overview Information
    overview = graphene.Field(DatasetOverview)

    # Boolean indicating if dataset backend is fully configured
    backend_is_configured = graphene.Boolean()

    # List of DatasetConfigurationParameter objects with the current configuration (excluding default config)
    backend_configuration = graphene.List(DatasetConfigurationParameter)

    # List of file keys for files that don't match hash values.
    # Managed datasets should always return 0 files.
    # Unmanaged datasets may return files, which indicates they most likely changed in the backend and the dataset
    # must be "updated" to include the new hashes as a new version
    content_hash_mismatches = graphene.List(graphene.String)

    # Temporary commits behind field before full branching is supported to indicate if a dataset is out of date
    commits_behind = graphene.Int()

    @classmethod
    def get_node(cls, info, id):
        """Method to resolve the object based on it's Node ID"""
        # Parse the key
        owner, name = id.split("&")

        return Dataset(id="{}&{}".format(owner, name),
                       name=name, owner=owner)

    def resolve_id(self, info):
        """Resolve the unique Node id for this object"""
        if not self.id:
            if not self.owner or not self.name:
                raise ValueError("Resolving a Dataset Node ID requires owner and name to be set")
            self.id = f"{self.owner}&{self.name}"

        return self.id

    def resolve_overview(self, info):
        """"""
        return DatasetOverview(id=f"{self.owner}&{self.name}", owner=self.owner, name=self.name)

    def resolve_description(self, info):
        """Get number of commits the active_branch is behind its remote counterpart.
        Returns 0 if up-to-date or if local only."""
        r = DatasetCacheController.build()
        return r.cached_description((get_logged_in_username(), self.owner, self.name))

    def resolve_schema_version(self, info):
        """Get number of commits the active_branch is behind its remote counterpart.
        Returns 0 if up-to-date or if local only."""
        return info.context.dataset_loader.load(f"{get_logged_in_username()}&{self.owner}&{self.name}").then(
            lambda dataset: dataset.schema)

    def resolve_created_on_utc(self, info):
        """Return the creation timestamp (if available - otherwise empty string)

        Args:
            info:

        Returns:

        """
        r = DatasetCacheController.build()
        return r.cached_created_time((get_logged_in_username(), self.owner, self.name))

    def _fetch_collaborators(self, dataset, info):
        """Helper method to fetch this dataset's collaborators

        Args:
            info: The graphene info object for this requests

        """
        # TODO: Future work will look up remote in LabBook data, allowing user to select remote.
        default_remote = dataset.client_config.config['git']['default_remote']
        admin_service = None
        for remote in dataset.client_config.config['git']['remotes']:
            if default_remote == remote:
                admin_service = dataset.client_config.config['git']['remotes'][remote]['admin_service']
                break

        # Extract valid Bearer token
        if "HTTP_AUTHORIZATION" in info.context.headers.environ:
            token = parse_token(info.context.headers.environ["HTTP_AUTHORIZATION"])
        else:
            raise ValueError("Authorization header not provided. Must have a valid session to query for collaborators")

        # Get collaborators from remote service
        mgr = GitLabManager(default_remote, admin_service, token)
        try:
            self._collaborators = [Collaborator(owner=self.owner, name=self.name,
                                                collaborator_username=c[1],
                                                permission=ProjectPermissions(c[2]).name)
                                   for c in mgr.get_collaborators(self.owner, self.name)]
        except ValueError:
            # If ValueError Raised, assume repo doesn't exist yet
            self._collaborators = []

    def helper_resolve_collaborators(self, dataset, info):
        """Helper method to fetch this dataset's collaborators and generate the resulting list of collaborators

        Args:
            info: The graphene info object for this requests

        """
        self._fetch_collaborators(dataset, info)
        return self._collaborators

    def resolve_collaborators(self, info):
        """Method to get the list of collaborators for a dataset

        Args:
            info:

        Returns:

        """
        if self._collaborators is None:
            # If here, put the fetch for collaborators in the promise
            return info.context.dataset_loader.load(f"{get_logged_in_username()}&{self.owner}&{self.name}").then(
                lambda dataset: self.helper_resolve_collaborators(dataset, info))
        else:
            return self._collaborators

    def helper_resolve_can_manage_collaborators(self, dataset, info):
        """Helper method to fetch this dataset's collaborators and check if user can manage collaborators

        Args:
            info: The graphene info object for this requests

        """
        self._fetch_collaborators(dataset, info)
        username = get_logged_in_username()
        for c in self._collaborators:
            if c.collaborator_username == username:
                if c.permission == ProjectPermissions.OWNER.name:
                    return True

        return False

    def resolve_can_manage_collaborators(self, info):
        """Method to check if the user is the "owner" of the dataset and can manage collaborators

        Args:
            info:

        Returns:

        """
        if self._collaborators is None:
            # If here, put the fetch for collaborators in the promise
            return info.context.dataset_loader.load(f"{get_logged_in_username()}&{self.owner}&{self.name}").then(
                lambda dataset: self.helper_resolve_can_manage_collaborators(dataset, info))

        username = get_logged_in_username()
        for c in self._collaborators:
            if c[1] == username and c[2] == ProjectPermissions.OWNER.name:
                return True
        return False

    def resolve_modified_on_utc(self, info):
        """Return the creation timestamp (if available - otherwise empty string)

        Args:
            args:
            context:
            info:

        Returns:

        """
        r = DatasetCacheController.build()
        return r.cached_modified_on((get_logged_in_username(), self.owner, self.name))

    def helper_resolve_activity_records(self, dataset, kwargs):
        """Helper method to generate ActivityRecord objects and populate the connection"""
        # Create instance of ActivityStore for this dataset
        store = ActivityStore(dataset)

        if kwargs.get('before') or kwargs.get('last'):
            raise ValueError("Only `after` and `first` arguments are supported when paging activity records")

        # Get edges and cursors
        edges = store.get_activity_records(after=kwargs.get('after'), first=kwargs.get('first'))
        if edges:
            cursors = [x.commit for x in edges]
        else:
            cursors = []

        # Get ActivityRecordObject instances
        edge_objs = []
        for edge, cursor in zip(edges, cursors):
            edge_objs.append(
                ActivityConnection.Edge(node=ActivityRecordObject(id=f"dataset&{self.owner}&{self.name}&{edge.commit}",
                                                                  owner=self.owner,
                                                                  name=self.name,
                                                                  _repository_type='dataset',
                                                                  commit=edge.commit,
                                                                  _activity_record=edge),
                                        cursor=cursor))

        # Create page info based on first commit. Since only paging backwards right now, just check for commit
        if edges:
            has_next_page = True

            # Get the message of the linked commit and check if it is the non-activity record dataset creation commit
            if len(edges) > 1:
                if edges[-2].linked_commit != "no-linked-commit":
                    linked_msg = dataset.git.log_entry(edges[-2].linked_commit)['message']
                    if linked_msg == f"Creating new empty Dataset: {dataset.name}" and "_GTM_ACTIVITY_" not in linked_msg:
                        # if you get here, this is the first activity record
                        has_next_page = False

            end_cursor = cursors[-1]
        else:
            has_next_page = False
            end_cursor = None

        page_info = graphene.relay.PageInfo(has_next_page=has_next_page, has_previous_page=False, end_cursor=end_cursor)

        return ActivityConnection(edges=edge_objs, page_info=page_info)

    def resolve_activity_records(self, info, **kwargs):
        """Method to page through branch Refs

        Args:
            kwargs:
            info:

        Returns:

        """
        return info.context.dataset_loader.load(f"{get_logged_in_username()}&{self.owner}&{self.name}").then(
            lambda dataset: self.helper_resolve_activity_records(dataset, kwargs))

    def resolve_detail_record(self, info, key):
        """Method to resolve the detail record object

        Args:
            args:
            info:

        Returns:

        """
        return ActivityDetailObject(id=f"dataset&{self.owner}&{self.name}&{key}",
                                    owner=self.owner,
                                    name=self.name,
                                    _repository_type='dataset',
                                    key=key)

    def resolve_detail_records(self, info, keys):
        """Method to resolve multiple detail record objects

        Args:
            args:
            info:

        Returns:

        """
        return [ActivityDetailObject(id=f"dataset&{self.owner}&{self.name}&{key}",
                                     owner=self.owner,
                                     name=self.name,
                                     _repository_type='dataset',
                                     key=key) for key in keys]

    def resolve_dataset_type(self, info, **kwargs):
        """Method to resolve a DatasetType object for the Dataset

        Args:
            args:
            info:

        Returns:

        """
        return info.context.dataset_loader.load(f"{get_logged_in_username()}&{self.owner}&{self.name}").then(
            lambda dataset: DatasetType(id=dataset.storage_type, storage_type=dataset.storage_type))

    def helper_resolve_all_files(self, dataset, kwargs):
        """Helper method to populate the DatasetFileConnection"""
        manifest = Manifest(dataset, get_logged_in_username())

        if "after" in kwargs:
            after_index = int(base64.b64decode(kwargs["after"]))
        else:
            after_index = 0

        # Generate naive cursors
        edges, indexes = manifest.list(first=kwargs.get("first"), after_index=after_index)
        cursors = [base64.b64encode("{}".format(x).encode("UTF-8")).decode("UTF-8") for x in indexes]

        edge_objs = []
        for edge, cursor in zip(edges, cursors):
            create_data = {"owner": self.owner,
                           "name": self.name,
                           "key": edge['key'],
                           "_file_info": edge}
            edge_objs.append(DatasetFileConnection.Edge(node=DatasetFile(**create_data), cursor=cursor))

        has_previous_page = False
        has_next_page = len(edges) > 0
        start_cursor = None
        end_cursor = None
        if cursors:
            start_cursor = cursors[0]
            end_cursor = cursors[-1]
            if indexes[-1] == len(manifest.manifest) - 1:
                has_next_page = False

        if kwargs.get("after"):
            if int(base64.b64decode(kwargs["after"])) > 0:
                has_previous_page = True

        page_info = graphene.relay.PageInfo(has_next_page=has_next_page, has_previous_page=has_previous_page,
                                            start_cursor=start_cursor, end_cursor=end_cursor)

        return DatasetFileConnection(edges=edge_objs, page_info=page_info)

    def resolve_all_files(self, info, **kwargs):
        """Resolver for getting all files in a Dataset"""
        return info.context.dataset_loader.load(f"{get_logged_in_username()}&{self.owner}&{self.name}").then(
            lambda dataset: self.helper_resolve_all_files(dataset, kwargs))

    @staticmethod
    def helper_resolve_visibility(dataset, info):
        # TODO: Future work will look up remote in Dataset data, allowing user to select remote.
        default_remote = dataset.client_config.config['git']['default_remote']
        admin_service = None
        for remote in dataset.client_config.config['git']['remotes']:
            if default_remote == remote:
                admin_service = dataset.client_config.config['git']['remotes'][remote]['admin_service']
                break

        # Extract valid Bearer token
        if "HTTP_AUTHORIZATION" in info.context.headers.environ:
            token = parse_token(info.context.headers.environ["HTTP_AUTHORIZATION"])
        else:
            raise ValueError("Authorization header not provided. Must have a valid session to query for collaborators")

        # Get collaborators from remote service
        mgr = GitLabManager(default_remote, admin_service, token)
        try:
            owner = InventoryManager().query_owner(dataset)
            d = mgr.repo_details(namespace=owner, repository_name=dataset.name)
            return d.get('visibility')
        except GitLabException:
            return "local"

    def resolve_visibility(self, info):
        """ Return string indicating visibility of project from GitLab:
         "public", "private", or "internal". """

        return info.context.dataset_loader.load(f"{get_logged_in_username()}&{self.owner}&{self.name}").then(
            lambda dataset: self.helper_resolve_visibility(dataset, info))

    @staticmethod
    def helper_resolve_default_remote(dataset):
        """Helper to extract the default remote from a dataset"""
        remotes = dataset.git.list_remotes()
        if remotes:
            url = [x['url'] for x in remotes if x['name'] == 'origin']
            if url:
                url = url[0]
                if "http" in url and url[-4:] != ".git":
                    logger.warning(f"Fixing remote URL format: {dataset.name}: {url}")
                    url = f"{url}.git"
                return url
            else:
                dataset.warning(f"There exist remotes in {str(dataset)}, but no origin found.")
        return None

    def resolve_default_remote(self, info):
        """Return True if no untracked files and no uncommitted changes (i.e., Git repo clean)

        Args:
            args:
            context:
            info:

        Returns:

        """
        return info.context.dataset_loader.load(f"{get_logged_in_username()}&{self.owner}&{self.name}").then(
            lambda dataset: self.helper_resolve_default_remote(dataset))

    @staticmethod
    def _helper_configure_default_parameters(dataset):
        """Helper to load the default configuration at runtime"""
        dataset.backend.set_default_configuration(get_logged_in_username(),
                                                  flask.g.get('access_token', None),
                                                  flask.g.get('id_token', None))
        return dataset

    def resolve_backend_is_configured(self, info):
        """Field to check if a dataset backend is fully configured"""
        return info.context.dataset_loader.load(f"{get_logged_in_username()}&{self.owner}&{self.name}").then(
            lambda dataset: self._helper_configure_default_parameters(dataset).backend.is_configured)

    def helper_resolve_backend_configuration(self, dataset):
        """Helper populate backend configuration fields"""
        dataset = self._helper_configure_default_parameters(dataset)
        missing_config = list()
        for item in dataset.backend.safe_current_configuration:
            missing_config.append(DatasetConfigurationParameter(parameter=item['parameter'],
                                                                description=item['description'],
                                                                parameter_type=item['type']))
        return missing_config

    def resolve_backend_configuration(self, info):
        """Field to get current configuration. If values are None, still needs to be set."""
        return info.context.dataset_loader.load(f"{get_logged_in_username()}&{self.owner}&{self.name}").then(
            lambda dataset: self.helper_resolve_backend_configuration(dataset))

    def resolve_content_hash_mismatches(self, info):
        """Field to look up any content hash mismatches. Note this can be slow for big datasets!"""
        return info.context.dataset_loader.load(f"{get_logged_in_username()}&{self.owner}&{self.name}").then(
            lambda dataset: dataset.backend.verify_contents(dataset, logger.info))

    def helper_resolve_commits_behind(self, dataset):
        """Helper to get the commits behind for a dataset. Used for linked datasets to see if
        they are out of date"""
        bm = BranchManager(dataset)
        bm.fetch()
        return bm.get_commits_behind(branch_name='master')

    def resolve_commits_behind(self, info):
        """Method to get the commits behind for a dataset. Used for linked datasets to see if
        they are out of date

        Args:
            args:
            context:
            info:

        Returns:

        """
        return info.context.dataset_loader.load(f"{get_logged_in_username()}&{self.owner}&{self.name}").then(
            lambda dataset: self.helper_resolve_commits_behind(dataset))
