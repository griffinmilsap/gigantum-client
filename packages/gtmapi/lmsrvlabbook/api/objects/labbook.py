import graphene
import flask

from gtmcore.logging import LMLogger
from gtmcore.dispatcher import Dispatcher
from gtmcore.inventory.branching import BranchManager
from gtmcore.inventory.inventory import InventoryManager, InventoryException
from gtmcore.labbook.schemas import CURRENT_SCHEMA
from gtmcore.activity import ActivityStore
from gtmcore.workflows.gitlab import GitLabManager, ProjectPermissions, GitLabException
from gtmcore.workflows import LabbookWorkflow
from gtmcore.files import FileOperations
from gtmcore.environment.utils import get_package_manager

from lmsrvcore.caching import LabbookCacheController
from lmsrvcore.auth.user import get_logged_in_username
from lmsrvcore.api.interfaces import GitRepository
from lmsrvcore.auth.identity import get_identity_manager_instance
from lmsrvcore.auth.identity import tokens_from_request_context

from lmsrvlabbook.api.objects.jobstatus import JobStatus
from lmsrvlabbook.api.objects.environment import Environment
from lmsrvlabbook.api.objects.collaborator import Collaborator
from lmsrvlabbook.api.objects.commit import Branch
from lmsrvlabbook.api.objects.overview import LabbookOverview
from lmsrvlabbook.api.objects.ref import LabbookRef
from lmsrvlabbook.api.objects.labbooksection import LabbookSection
from lmsrvlabbook.api.connections.activity import ActivityConnection
from lmsrvlabbook.api.objects.activity import ActivityDetailObject, ActivityRecordObject
from lmsrvlabbook.api.objects.packagecomponent import PackageComponent, PackageComponentInput
from lmsrvlabbook.api.objects.dataset import Dataset
from lmsrvlabbook.dataloader.package import PackageDataloader
from lmsrvlabbook.dataloader.fetch import FetchLoader

logger = LMLogger.get_logger()


class Labbook(graphene.ObjectType):
    """A type representing a LabBook and all of its contents

    LabBooks are uniquely identified by both the "owner" and the "name" of the LabBook

    """
    class Meta:
        interfaces = (graphene.relay.Node, GitRepository)

    # Store collaborator data so it is only fetched once per request
    _collaborators = None

    # A short description of the LabBook limited to 140 UTF-8 characters
    description = graphene.String()

    # Data schema version of this labbook. It may be behind the most recent version and need
    # to be upgraded.
    schema_version = graphene.Int()

    # Indicates whether the current schema is behind.
    is_deprecated = graphene.Boolean()
    should_migrate = graphene.Boolean()

    # Size on disk of LabBook in bytes
    # NOTE: This is a string since graphene can't represent ints bigger than 2**32
    size_bytes = graphene.String()

    # Name of currently active (checked-out) branch
    active_branch_name = graphene.String()

    # Primary user branch of repo (known also as "Workspace Branch" or "trunk")
    workspace_branch_name = graphene.String()

    # List of branch objects
    branches = graphene.List(Branch)

    # Get the URL of the remote origin
    default_remote = graphene.String()

    # Creation date/timestamp in UTC in ISO format
    creation_date_utc = graphene.types.datetime.DateTime()

    # Modified date/timestamp in UTC in ISO format
    modified_on_utc = graphene.types.datetime.DateTime()

    # List of collaborators
    collaborators = graphene.List(Collaborator)

    # A boolean indicating if the current user can manage collaborators
    can_manage_collaborators = graphene.Boolean()

    # Whether repo state is clean
    is_repo_clean = graphene.Boolean()

    # Environment Information
    environment = graphene.Field(Environment)

    # Overview Information
    overview = graphene.Field(LabbookOverview)

    # List of sections
    code = graphene.Field(LabbookSection)
    input = graphene.Field(LabbookSection)
    output = graphene.Field(LabbookSection)

    # Connection to Activity Entries
    activity_records = graphene.relay.ConnectionField(ActivityConnection)

    # Access a detail record directly, which is useful when fetching detail items
    detail_record = graphene.Field(ActivityDetailObject, key=graphene.String())
    detail_records = graphene.List(ActivityDetailObject, keys=graphene.List(graphene.String))

    # List of keys of all background jobs pertaining to this labbook (queued, started, failed, etc.)
    background_jobs = graphene.List(JobStatus)

    # Package Query for validating packages and getting PackageComponents by attributes
    check_packages = graphene.List(PackageComponent, package_input=graphene.List(PackageComponentInput))

    visibility = graphene.String()

    # List of Datasets that are linked to this Labbook
    linked_datasets = graphene.List(Dataset)

    @classmethod
    def get_node(cls, info, id):
        """Method to resolve the object based on it's Node ID"""
        # Parse the key
        owner, name = id.split("&")

        return Labbook(id="{}&{}".format(owner, name),
                       name=name, owner=owner)

    def resolve_id(self, info):
        """Resolve the unique Node id for this object"""
        if not self.id:
            if not self.owner or not self.name:
                raise ValueError("Resolving a Labbook Node ID requires owner and name to be set")
            self.id = f"{self.owner}&{self.name}"

        return self.id

    def resolve_description(self, info):
        """Return the description. """
        r = LabbookCacheController()
        return r.cached_description((get_logged_in_username(), self.owner, self.name))

    def resolve_environment(self, info):
        """"""
        return Environment(id=f"{self.owner}&{self.name}", owner=self.owner, name=self.name)

    def resolve_overview(self, info):
        """"""
        return LabbookOverview(id=f"{self.owner}&{self.name}", owner=self.owner, name=self.name)

    def resolve_schema_version(self, info):
        """Get number of commits the active_branch is behind its remote counterpart.
        Returns 0 if up-to-date or if local only."""
        return info.context.labbook_loader.load(f"{get_logged_in_username()}&{self.owner}&{self.name}").then(
            lambda labbook: labbook.schema)

    def resolve_is_deprecated(self, info):
        """ Returns True if the project schema lags the current schema and should be migrated """
        return info.context.labbook_loader.load(f"{get_logged_in_username()}&{self.owner}&{self.name}").then(
            lambda labbook: labbook.schema != CURRENT_SCHEMA)

    def resolve_should_migrate(self, info):
        def _should_migrate(lb):
            wf = LabbookWorkflow(lb)
            return wf.should_migrate()
        return info.context.labbook_loader.load(f"{get_logged_in_username()}&{self.owner}&{self.name}").then(
            lambda labbook: _should_migrate(labbook))

    def resolve_size_bytes(self, info):
        """Return the size of the labbook on disk (in bytes).
        NOTE! This must be a string, as graphene can't quite handle big integers. """
        return info.context.labbook_loader.load(f"{get_logged_in_username()}&{self.owner}&{self.name}").then(
            lambda labbook: str(FileOperations.content_size(labbook)))

    def resolve_active_branch_name(self, info):
        return info.context.labbook_loader.load(f"{get_logged_in_username()}&{self.owner}&{self.name}").then(
            lambda labbook: BranchManager(labbook, username=get_logged_in_username()).active_branch)

    def resolve_workspace_branch_name(self, info):
        return info.context.labbook_loader.load(f"{get_logged_in_username()}&{self.owner}&{self.name}").then(
            lambda labbook: BranchManager(labbook, username=get_logged_in_username()).workspace_branch)

    def resolve_available_branch_names(self, info):
        fltr = lambda labbook: \
            BranchManager(labbook, username=get_logged_in_username()).branches_local
        return info.context.labbook_loader.load(f"{get_logged_in_username()}&{self.owner}&{self.name}").then(
            fltr)

    def resolve_local_branch_names(self, info):
        fltr = lambda labbook: \
            BranchManager(labbook, username=get_logged_in_username()).branches_local
        return info.context.labbook_loader.load(f"{get_logged_in_username()}&{self.owner}&{self.name}").then(
            fltr)

    def resolve_remote_branch_names(self, info):
        fltr = lambda labbook: \
            BranchManager(labbook, username=get_logged_in_username()).branches_remote
        return info.context.labbook_loader.load(f"{get_logged_in_username()}&{self.owner}&{self.name}").then(
            fltr)

    def resolve_mergeable_branch_names(self, info):
        def _mergeable(lb):
            # TODO(billvb) - Refactor for new branch model.
            username = get_logged_in_username()
            bm = BranchManager(lb, username=username)
            return [b for b in bm.branches_local if bm.active_branch != b]

        return info.context.labbook_loader.load(f"{get_logged_in_username()}&{self.owner}&{self.name}").then(
            _mergeable)

    def helper_resolve_active_branch(self, labbook):
        active_branch_name = BranchManager(labbook, username=get_logged_in_username()).active_branch
        return LabbookRef(id=f"{self.owner}&{self.name}&None&{active_branch_name}",
                          owner=self.owner, name=self.name, prefix=None,
                          ref_name=active_branch_name)

    def resolve_active_branch(self, info):
        """Method to get the active branch as a LabbookRef object"""
        return info.context.labbook_loader.load(f"{get_logged_in_username()}&{self.owner}&{self.name}").then(
                lambda labbook: self.helper_resolve_active_branch(labbook))

    def resolve_is_repo_clean(self, info):
        """Return True if no untracked files and no uncommitted changes (i.e., Git repo clean)"""
        return info.context.labbook_loader.load(f"{get_logged_in_username()}&{self.owner}&{self.name}").then(
            lambda labbook: labbook.is_repo_clean)

    def resolve_creation_date_utc(self, info):
        """Return the creation timestamp (if available - otherwise empty string)

        Args:
            args:
            context:
            info:

        Returns:

        """
        r = LabbookCacheController()
        return r.cached_created_time((get_logged_in_username(), self.owner, self.name))

    def resolve_modified_on_utc(self, info):
        """Return the modified on timestamp

        Args:
            args:
            context:
            info:

        Returns:

        """
        r = LabbookCacheController()
        return r.cached_modified_on((get_logged_in_username(), self.owner, self.name))

    @staticmethod
    def helper_resolve_default_remote(labbook):
        """Helper to extract the default remote from a labbook"""
        remotes = labbook.git.list_remotes()
        if remotes:
            url = [x['url'] for x in remotes if x['name'] == 'origin']
            if url:
                return url[0]
            else:
                logger.warning(f"There exist remotes in {str(labbook)}, but no origin found.")
        return None

    def resolve_default_remote(self, info):
        """Return True if no untracked files and no uncommitted changes (i.e., Git repo clean)

        Args:
            args:
            context:
            info:

        Returns:

        """
        return info.context.labbook_loader.load(f"{get_logged_in_username()}&{self.owner}&{self.name}").then(
            lambda labbook: self.helper_resolve_default_remote(labbook))

    def helper_resolve_branches(self, lb, kwargs):
        bm = BranchManager(lb)

        fetcher = FetchLoader()

        return [Branch(_fetch_loader=fetcher, owner=self.owner, name=self.name, branch_name=b)
                for b in sorted(set(bm.branches_local + bm.branches_remote))]

    def resolve_branches(self, info, **kwargs):
        """Method to page through branch Refs

        Args:
            args:
            context:
            info:

        Returns:

        """
        return info.context.labbook_loader.load(f"{get_logged_in_username()}&{self.owner}&{self.name}").then(
            lambda labbook: self.helper_resolve_branches(labbook, kwargs))

    def resolve_code(self, info):
        """Method to resolve the code section"""
        return LabbookSection(id="{}&{}&{}".format(self.owner, self.name, 'code'),
                              owner=self.owner, name=self.name, section='code')

    def resolve_input(self, info):
        """Method to resolve the input section"""
        return LabbookSection(id="{}&{}&{}".format(self.owner, self.name, 'input'),
                              owner=self.owner, name=self.name, section='input')

    def resolve_output(self, info):
        """Method to resolve the output section"""
        return LabbookSection(id="{}&{}&{}".format(self.owner, self.name, 'output'),
                              owner=self.owner, name=self.name, section='output')

    def helper_resolve_activity_records(self, labbook, kwargs):
        """Helper method to generate ActivityRecord objects and populate the connection"""
        # Create instance of ActivityStore for this LabBook
        store = ActivityStore(labbook)

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
                ActivityConnection.Edge(node=ActivityRecordObject(id=f"labbook&{self.owner}&{self.name}&{edge.commit}",
                                                                  owner=self.owner,
                                                                  name=self.name,
                                                                  _repository_type='labbook',
                                                                  commit=edge.commit,
                                                                  _activity_record=edge),
                                        cursor=cursor))

        # Create page info based on first commit. Since only paging backwards right now, just check for commit
        if edges:
            has_next_page = True

            # Get the message of the linked commit and check if it is the non-activity record labbook creation commit
            if edges[-1].linked_commit != "no-linked-commit":
                linked_msg = labbook.git.log_entry(edges[-1].linked_commit)['message']
                if linked_msg == f"Creating new empty LabBook: {labbook.name}" and "_GTM_ACTIVITY_" not in linked_msg:
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
        return info.context.labbook_loader.load(f"{get_logged_in_username()}&{self.owner}&{self.name}").then(
            lambda labbook: self.helper_resolve_activity_records(labbook, kwargs))

    def resolve_detail_record(self, info, key):
        """Method to resolve the detail record object

        Args:
            args:
            info:

        Returns:

        """
        return ActivityDetailObject(id=f"labbook&{self.owner}&{self.name}&{key}",
                                    owner=self.owner,
                                    name=self.name,
                                    _repository_type='labbook',
                                    key=key)

    def resolve_detail_records(self, info, keys):
        """Method to resolve multiple detail record objects

        Args:
            args:
            info:

        Returns:

        """
        return [ActivityDetailObject(id=f"labbook&{self.owner}&{self.name}&{key}",
                                     owner=self.owner,
                                     name=self.name,
                                     _repository_type='labbook',
                                     key=key) for key in keys]

    def _fetch_collaborators(self, labbook, info):
        """Helper method to fetch this labbook's collaborators

        Args:
            info: The graphene info object for this requests

        """
        if self._collaborators is None:
            config = flask.current_app.config['LABMGR_CONFIG']
            remote_config = config.get_remote_configuration()

            # Get tokens from request context
            access_token, id_token = tokens_from_request_context(tokens_required=True)

            mgr = GitLabManager(remote_config['git_remote'],
                                remote_config['hub_api'],
                                access_token=access_token,
                                id_token=id_token)
            try:
                self._collaborators = [Collaborator(owner=self.owner, name=self.name,
                                                    collaborator_username=c[1],
                                                    permission=ProjectPermissions(c[2]).name)
                                       for c in mgr.get_collaborators(self.owner, self.name)]
            except ValueError:
                # If ValueError Raised, assume repo doesn't exist yet
                self._collaborators = []
        else:
            return self._collaborators

    def helper_resolve_collaborators(self, labbook, info):
        """Helper method to fetch this labbook's collaborators and generate the resulting list of collaborators

        Args:
            info: The graphene info object for this requests

        """
        self._fetch_collaborators(labbook, info)
        return self._collaborators

    def resolve_collaborators(self, info):
        """Method to get the list of collaborators for a labbook

        Args:
            info:

        Returns:

        """
        if self._collaborators is None:
            # If here, put the fetch for collaborators in the promise
            return info.context.labbook_loader.load(f"{get_logged_in_username()}&{self.owner}&{self.name}").then(
                lambda labbook: self.helper_resolve_collaborators(labbook, info))
        else:
            return self._collaborators

    def helper_resolve_can_manage_collaborators(self, labbook, info):
        """Helper method to fetch this labbook's collaborators and check if user can manage collaborators

        Args:
            info: The graphene info object for this requests

        """
        self._fetch_collaborators(labbook, info)
        username = get_logged_in_username()
        for c in self._collaborators:
            if c.collaborator_username == username:
                if c.permission == ProjectPermissions.OWNER.name:
                    return True

        return False

    def resolve_can_manage_collaborators(self, info):
        """Method to check if the user is the "owner" of the labbook and can manage collaborators

        Args:
            info:

        Returns:

        """
        if self._collaborators is None:
            # If here, put the fetch for collaborators in the promise
            return info.context.labbook_loader.load(f"{get_logged_in_username()}&{self.owner}&{self.name}").then(
                lambda labbook: self.helper_resolve_can_manage_collaborators(labbook, info))

        username = get_logged_in_username()
        for c in self._collaborators:
            if c[1] == username and c[2] == ProjectPermissions.OWNER.name:
                return True
        return False

    @staticmethod
    def helper_resolve_background_jobs(labbook):
        """Helper to generate background job info from a labbook"""
        d = Dispatcher()
        jobs = d.get_jobs_for_labbook(labbook_key=labbook.key)
        return [JobStatus(j.job_key.key_str) for j in jobs]

    def resolve_background_jobs(self, info):
        """ Return the job keys, tasks, and statuses for all background jobs. """
        return info.context.labbook_loader.load(f"{get_logged_in_username()}&{self.owner}&{self.name}").then(
            lambda labbook: self.helper_resolve_background_jobs(labbook))

    @staticmethod
    def helper_resolve_check_packages(labbook, package_input):
        """Helper to return a list of PackageComponent objects that have been validated"""
        manager = list(set([x['manager'] for x in package_input]))

        if len(manager) > 1:
            raise ValueError("Only batch add via 1 package manager at a time.")

        # Instantiate appropriate package manager
        mgr = get_package_manager(manager[0])

        # Validate packages
        pkg_result = mgr.validate_packages(package_input, labbook, get_logged_in_username())

        # Create dataloader
        keys = [f"{manager[0]}&{pkg.package}" for pkg in pkg_result]
        vd = PackageDataloader(keys, labbook, get_logged_in_username())

        # Return object
        return [PackageComponent(_dataloader=vd,
                                 manager=manager[0],
                                 package=pkg.package,
                                 version=pkg.version,
                                 is_valid=not pkg.error) for pkg in pkg_result]

    def resolve_check_packages(self, info, package_input):
        """Method to retrieve package component. Errors can be used to validate if a package name and version
        are correct

        Returns:
            list(PackageComponent)
        """
        return info.context.labbook_loader.load(f"{get_logged_in_username()}&{self.owner}&{self.name}").then(
            lambda labbook: self.helper_resolve_check_packages(labbook, package_input))

    @staticmethod
    def helper_resolve_visibility(labbook, info):
        if not get_identity_manager_instance().allow_server_access:
            return 'local'
        else:
            # Get remote server configuration
            config = flask.current_app.config['LABMGR_CONFIG']
            remote_config = config.get_remote_configuration()

            # Get tokens from request context
            access_token, id_token = tokens_from_request_context(tokens_required=True)

            mgr = GitLabManager(remote_config['git_remote'],
                                remote_config['hub_api'],
                                access_token=access_token,
                                id_token=id_token)
            try:
                owner = InventoryManager().query_owner(labbook)
                d = mgr.repo_details(namespace=owner, repository_name=labbook.name)
                assert 'visibility' in d.keys(), 'Visibility is not in repo details response keys'
                return d.get('visibility')
            except GitLabException:
                return "local"

    def resolve_visibility(self, info):
        """ Return string indicating visibility of project from GitLab:
         "public", "private", or "internal". """

        return info.context.labbook_loader.load(f"{get_logged_in_username()}&{self.owner}&{self.name}").then(
            lambda labbook: self.helper_resolve_visibility(labbook, info))

    @staticmethod
    def helper_resolve_linked_datasets(labbook, info):
        dataset_objs = InventoryManager().get_linked_datasets(labbook)
        datasets = list()
        for ds in dataset_objs:
            try:
                # Prime the dataset loader, so when fields are resolved they resolve from these LINKED dataset
                # directories inside the project, and not the normal location
                info.context.dataset_loader.prime(f"{get_logged_in_username()}&{ds.namespace}&{ds.name}", ds)
                datasets.append(Dataset(owner=ds.namespace, name=ds.name))
            except InventoryException:
                continue

        return datasets

    def resolve_linked_datasets(self, info):
        """ """
        return info.context.labbook_loader.load(f"{get_logged_in_username()}&{self.owner}&{self.name}").then(
            lambda labbook: self.helper_resolve_linked_datasets(labbook, info))
