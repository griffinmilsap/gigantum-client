import base64
import graphene
import os

from gtmcore.files import FileOperations
from gtmcore.logging import LMLogger

from lmsrvcore.auth.user import get_logged_in_username
from lmsrvcore.api.interfaces import GitRepository
from lmsrvcore.api.connections import ListBasedConnection

from lmsrvlabbook.api.objects.labbookfile import LabbookFile
from lmsrvlabbook.api.connections.labbookfileconnection import LabbookFileConnection
import redis
import json

logger = LMLogger.get_logger()


class LabbookSection(graphene.ObjectType):
    """A type representing a section within a LabBook (i.e., code, input, output)
    """
    class Meta:
        interfaces = (graphene.relay.Node, GitRepository)

    # Section name (code, input, output)
    section = graphene.String()

    # List of files and directories, given a relative root directory within the section
    files = graphene.relay.ConnectionField(LabbookFileConnection, root_dir=graphene.String())

    # List of all files and directories within the section
    all_files = graphene.relay.ConnectionField(LabbookFileConnection)

    has_files = graphene.Boolean()

    @classmethod
    def get_node(cls, info, id):
        """Method to resolve the object based on it's Node ID"""
        # Parse the key
        owner, name, section = id.split("&")

        return LabbookSection(owner=owner, name=name, section=section)

    def resolve_id(self, info):
        """Resolve the unique Node id for this object"""
        if not self.id:
            if not self.owner or not self.name or not self.section:
                raise ValueError("Resolving a LabbookSection Node ID requires owner, name, and section to be set")

            self.id = f"{self.owner}&{self.name}&{self.section}"

        return self.id

    def helper_resolve_files(self, labbook, kwargs):
        """Helper method to populate the LabbookFileConnection"""
        base_dir = None
        if 'root_dir' in kwargs:
            if kwargs['root_dir']:
                base_dir = kwargs['root_dir'] + os.path.sep
                base_dir = base_dir.replace(os.path.sep + os.path.sep, os.path.sep)

        # Get all files and directories, with the exception of anything in .git or .gigantum
        edges = FileOperations.listdir(labbook, self.section, base_path=base_dir, show_hidden=False)

        # Generate naive cursors
        cursors = [base64.b64encode("{}".format(cnt).encode("UTF-8")).decode("UTF-8") for cnt, x in enumerate(edges)]

        # Process slicing and cursor args
        lbc = ListBasedConnection(edges, cursors, kwargs)
        lbc.apply()

        edge_objs = []
        for edge, cursor in zip(lbc.edges, lbc.cursors):
            create_data = {"owner": self.owner,
                           "section": self.section,
                           "name": self.name,
                           "key": edge['key'],
                           "_file_info": edge}
            edge_objs.append(LabbookFileConnection.Edge(node=LabbookFile(**create_data), cursor=cursor))

        return LabbookFileConnection(edges=edge_objs, page_info=lbc.page_info)

    def resolve_files(self, info, **kwargs):
        """Resolver for getting file listing in a single directory"""
        return info.context.labbook_loader.load(f"{get_logged_in_username()}&{self.owner}&{self.name}").then(
            lambda labbook: self.helper_resolve_files(labbook, kwargs))

    def resolve_has_files(self, info, **kwargs):
        def _hf(lb):
            p = os.path.join(lb.root_dir, self.section)
            for rootd, dirs, files in os.walk(p):
                for f in files:
                    if f != '.gitkeep':
                        return True
            return False

        return info.context.labbook_loader.load(f"{get_logged_in_username()}&{self.owner}&{self.name}").then(
            _hf
        )

    def helper_resolve_all_files(self, labbook, kwargs):
        """Helper method to populate the LabbookFileConnection"""
        # Check if file info has been cached
        redis_conn = redis.Redis(db=5)
        cache_key = f"FILE_LIST_CACHE|{labbook.key}|{self.section}"
        if redis_conn.exists(cache_key):
            # Load from cache
            edges = json.loads(redis_conn.get(cache_key).decode("utf-8"))
            redis_conn.expire(cache_key, 5)
        else:
            # Load from disk and cache
            # Get all files and directories, with the exception of anything in .git or .gigantum
            edges = FileOperations.walkdir(labbook, section=self.section, show_hidden=False)
            redis_conn.set(cache_key, json.dumps(edges))
            redis_conn.expire(cache_key, 5)

        # Generate naive cursors
        cursors = [base64.b64encode("{}".format(cnt).encode("UTF-8")).decode("UTF-8") for cnt, x in enumerate(edges)]

        # Process slicing and cursor args
        lbc = ListBasedConnection(edges, cursors, kwargs)
        lbc.apply()

        edge_objs = []
        for edge, cursor in zip(lbc.edges, lbc.cursors):
            create_data = {"owner": self.owner,
                           "section": self.section,
                           "name": self.name,
                           "key": edge['key'],
                           "_file_info": edge}
            edge_objs.append(LabbookFileConnection.Edge(node=LabbookFile(**create_data), cursor=cursor))

        return LabbookFileConnection(edges=edge_objs, page_info=lbc.page_info)

    def resolve_all_files(self, info, **kwargs):
        """Resolver for getting all files in a LabBook section"""
        return info.context.labbook_loader.load(f"{get_logged_in_username()}&{self.owner}&{self.name}").then(
            lambda labbook: self.helper_resolve_all_files(labbook, kwargs))
