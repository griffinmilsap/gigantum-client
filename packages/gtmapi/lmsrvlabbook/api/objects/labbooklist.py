import time
import base64
import graphene
import requests
import flask
from string import Template

from gtmcore.logging import LMLogger
from gtmcore.inventory.inventory import InventoryManager
from gtmcore.configuration import Configuration

from lmsrvcore.caching import LabbookCacheController
from lmsrvcore.auth.user import get_logged_in_username
from lmsrvcore.api.connections import ListBasedConnection
from lmsrvcore.auth.identity import tokens_from_request_context

from lmsrvlabbook.api.connections.labbook import LabbookConnection, Labbook
from lmsrvlabbook.api.connections.remotelabbook import RemoteLabbookConnection, RemoteLabbook

logger = LMLogger.get_logger()


class LabbookList(graphene.ObjectType):
    """A type simply used as a container to group local and remote LabBooks for better relay support

    Labbook and RemoteLabbook objects are uniquely identified by both the "owner" and the "name" of the LabBook

    NOTE: RemoteLabbooks require all fields to be explicitly set as there is no current way to asynchronously retrieve
          the data
    """
    class Meta:
        interfaces = (graphene.relay.Node, )

    # List of specific local labbooks based on Node ID
    local_by_id = graphene.List(Labbook, ids=graphene.List(graphene.String))

    # Connection to locally available labbooks
    local_labbooks = graphene.relay.ConnectionField(LabbookConnection,
                                                    order_by=graphene.String(default_value="name"),
                                                    sort=graphene.String(default_value="asc"))

    # Connection to remotely available labbooks
    remote_labbooks = graphene.relay.ConnectionField(RemoteLabbookConnection,
                                                     order_by=graphene.String(default_value="name"),
                                                     sort=graphene.String(default_value="asc"))

    @classmethod
    def get_node(cls, info, id):
        """Method to resolve the object based on it's Node ID"""
        # This object doesn't really have a node because it's simply container
        return LabbookList(id=id)

    def resolve_id(self, info):
        """Resolve the unique Node id for this object"""
        # This object doesn't really have a node because it's simply container
        return ""

    def resolve_local_by_id(self, info, ids):
        """Method to return graphene Labbook instances based on a list of Global Node IDs

        Uses the "currently logged in" user

        Args:
            ids(list): List of Node IDs for the local labbooks to return

        Returns:
            list(Labbook)
        """
        return [graphene.Node.get_node_from_global_id(info, x) for x in ids]

    def resolve_local_labbooks(self, info, order_by: str, sort: str, **kwargs):
        """Method to return all graphene Labbook instances for the logged in user available locally

        Uses the "currently logged in" user

        Args:
            order_by(str): String specifying how labbooks should be sorted
            sort(str): 'desc' for descending (default) 'asc' for ascending

        Returns:
            list(Labbook)
        """
        t0 = time.time()
        username = get_logged_in_username()

        if sort == "desc":
            reverse = True
        elif sort == "asc":
            reverse = False
        else:
            raise ValueError(f"Unsupported sort_str: {sort}. Use `desc`, `asc`")

        # Collect all labbooks for all owners
        inv_manager = InventoryManager()
        cache_controller = LabbookCacheController()
        ids = inv_manager.list_repository_ids(username, 'labbook')

        safe_ids = []
        for (uname, owner, project_name) in ids:
            try:
                cache_controller.cached_modified_on((username, owner, project_name))
                cache_controller.cached_created_time((username, owner, project_name))
                safe_ids.append((uname, owner, project_name))
            except Exception as e:
                logger.warning(f"Error loading LabBook {uname, owner, project_name}: {e}")

        if order_by == 'modified_on':
            sort_key = lambda tup: cache_controller.cached_modified_on(tup)
        elif order_by == 'created_on':
            sort_key = lambda tup: cache_controller.cached_created_time(tup)
        else:
            sort_key = lambda tup: tup[2]

        sorted_ids = sorted(safe_ids, key=sort_key)
        if reverse:
            sorted_ids.reverse()

        edges = [(tup[1], tup[2]) for tup in sorted_ids]
        cursors = [base64.b64encode("{}".format(cnt).encode("UTF-8")).decode("UTF-8") for cnt, x in enumerate(edges)]
        lbc = ListBasedConnection(edges, cursors, kwargs)
        lbc.apply()

        edge_objs = []
        for edge, cursor in zip(lbc.edges, lbc.cursors):
            create_data = {"id": "{}&{}".format(edge[0], edge[1]),
                           "name": edge[1],
                           "owner": edge[0]}

            edge_objs.append(LabbookConnection.Edge(node=Labbook(**create_data),
                                                    cursor=cursor))

        logger.info(f"Listed all projects in {time.time()-t0:.2f}sec")
        return LabbookConnection(edges=edge_objs, page_info=lbc.page_info)

    def resolve_remote_labbooks(self, info, order_by: str, sort: str, **kwargs):
        """Method to return a all RemoteLabbook instances for the logged in user

        This is a remote call, so should be fetched on its own and only when needed. The user must have a valid
        session for data to be returned.

        Args:
            order_by(str): String specifying how labbooks should be sorted
            sort(str): 'desc' for descending (default) 'asc' for ascending

        Supported order_by modes:
            - name: naturally sort on the name
            - created_on: sort by creation date
            - modified_on: sort by modification date

        Returns:
            list(Labbook)
        """
        # Load config class out of flask config obj
        config: Configuration = flask.current_app.config['LABMGR_CONFIG']

        if "last" in kwargs or "before" in kwargs:
            raise ValueError("Cannot page in reverse direction, must provide first/after parameters instead")

        # Prep arguments
        if "first" in kwargs:
            first = int(kwargs['first'])
        else:
            first = 8

        # Add optional arguments
        if "after" in kwargs:
            after = "\"" + kwargs['after'] + "\""
        else:
            after = "null"

        if order_by is not None:
            if order_by not in ['name', 'created_on', 'modified_on']:
                raise ValueError(f"Unsupported order_by: {order_by}. Use `name`, `created_on`, `modified_on`")
        else:
            order_by = 'last_activity_at'

        # Translate order by argument for gateway
        if order_by == "created_on":
            order_by = "created_at"

        if order_by == "modified_on":
            order_by = "last_activity_at"

        if sort is not None:
            if sort not in ['desc', 'asc']:
                raise ValueError(f"Unsupported sort: {sort}. Use `desc`, `asc`")
        else:
            sort = "desc"

        # Get tokens from request context
        access_token, id_token = tokens_from_request_context(tokens_required=True)

        query_template = Template("""
{
  repositories(orderBy: "$order_by", sort: "$sort", first: $first, after: $after){
    edges{
      node{
        ... on Project{
          id
          namespace
          repositoryName
          description
          visibility
          createdOnUtc
          modifiedOnUtc
        }
      }
      cursor
    }
    pageInfo{
      hasNextPage
      hasPreviousPage
      startCursor
      endCursor
    }
  }
}
""")
        query_str = query_template.substitute(order_by=order_by, sort=sort, first=str(first), after=after)
        # Query SaaS index service for data
        response = requests.post(config.get_hub_api_url(),
                                 json={"query": query_str},
                                 headers={"Authorization": f"Bearer {access_token}",
                                          "Identity": id_token,
                                          "Content-Type": "application/json"})

        if response.status_code != 200:
            raise IOError(f"Failed to retrieve Project listing from remote server: {response.json()}")
        response_data = response.json()
        if 'errors' in response_data:
            raise IOError(f"Failed to retrieve Project listing from remote server: {response_data['errors']}")

        remote_url = config.get_remote_configuration()['git_remote']
        # Get Labbook instances
        edge_objs = []
        for edge in response_data['data']['repositories']['edges']:
            node = edge['node']
            if node:
                create_data = {
                                "id": "{}&{}".format(node["namespace"], node["repositoryName"]),
                                "owner": node["namespace"],
                                "name": node["repositoryName"],
                                "description": node["description"],
                                "creation_date_utc": node["createdOnUtc"],
                                "modified_date_utc": node["modifiedOnUtc"],
                                "visibility": node["visibility"],
                                "import_url": f"https://{remote_url}/{node['namespace']}/{node['repositoryName']}.git"
                              }

                edge_objs.append(RemoteLabbookConnection.Edge(node=RemoteLabbook(**create_data),
                                                              cursor=edge['cursor']))

        # Create Page Info instance
        page_info_data = response_data['data']['repositories']['pageInfo']
        page_info = graphene.relay.PageInfo(has_next_page=page_info_data['hasNextPage'],
                                            has_previous_page=page_info_data['hasPreviousPage'],
                                            start_cursor=page_info_data['startCursor'],
                                            end_cursor=page_info_data['endCursor'])

        return RemoteLabbookConnection(edges=edge_objs, page_info=page_info)
