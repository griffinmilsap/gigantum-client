import base64
import graphene
import requests
import flask
import time
from natsort import natsorted
from string import Template

from gtmcore.logging import LMLogger
from gtmcore.inventory.inventory import InventoryManager
from gtmcore.configuration import Configuration

from lmsrvlabbook.api.connections.dataset import Dataset, DatasetConnection
from lmsrvlabbook.api.connections.remotedataset import RemoteDatasetConnection, RemoteDataset
from lmsrvcore.caching import DatasetCacheController
from lmsrvcore.auth.user import get_logged_in_username
from lmsrvcore.api.connections import ListBasedConnection
from lmsrvcore.auth.identity import tokens_from_request_context

logger = LMLogger.get_logger()


class DatasetList(graphene.ObjectType):
    """A type simply used as a container to group local and remote Datasets for better relay support

    Dataset and RemoteDataset objects are uniquely identified by both the "owner" and the "name" of the Dataset

    NOTE: RemoteDatasets require all fields to be explicitly set as there is no current way to asynchronously retrieve
          the data
    """
    class Meta:
        interfaces = (graphene.relay.Node,)

    # List of specific local datasets based on Node ID
    local_by_id = graphene.List(Dataset, ids=graphene.List(graphene.String))

    # Connection to locally available datasets
    local_datasets = graphene.relay.ConnectionField(DatasetConnection,
                                                    order_by=graphene.String(default_value="name"),
                                                    sort=graphene.String(default_value="asc"))

    # Connection to remotely available labbooks
    remote_datasets = graphene.relay.ConnectionField(RemoteDatasetConnection,
                                                     order_by=graphene.String(default_value="name"),
                                                     sort=graphene.String(default_value="asc"))

    @classmethod
    def get_node(cls, info, id):
        """Method to resolve the object based on it's Node ID"""
        # This object doesn't really have a node because it's simply container
        return DatasetList(id=id)

    def resolve_id(self, info):
        """Resolve the unique Node id for this object"""
        # This object doesn't really have a node because it's simply container
        return ""

    def resolve_local_by_id(self, info, ids):
        """Method to return graphene Dataset instances based on a list of Global Node IDs

        Uses the "currently logged in" user

        Args:
            ids(list): List of Node IDs for the local datasets to return

        Returns:
            list(Dataset)
        """
        return [graphene.Node.get_node_from_global_id(info, x) for x in ids]

    def resolve_local_datasets(self, info, order_by: str, sort: str, **kwargs):
        """Method to return all graphene Dataset instances for the logged in user available locally

        Uses the "currently logged in" user

        Args:
            order_by(str): String specifying how datasets should be sorted
            sort(str): 'desc' for descending, 'asc' for ascending (default)

        Returns:
            list(Dataset)
        """
        t0 = time.time()
        username = get_logged_in_username()

        if sort == "desc":
            reverse = True
        elif sort == "asc":
            reverse = False
        else:
            raise ValueError(f"Unsupported sort_str: {sort}. Use `desc`, `asc`")

        # Collect all datasets for all owners
        inv_manager = InventoryManager()
        cache_controller = DatasetCacheController()
        ids = inv_manager.list_repository_ids(username, 'dataset')

        safe_ids = []
        for (uname, owner, dataset_name) in ids:
            try:
                cache_controller.cached_modified_on((username, owner, dataset_name))
                cache_controller.cached_created_time((username, owner, dataset_name))
                safe_ids.append((uname, owner, dataset_name))
            except Exception as e:
                logger.warning(f"Error loading Dataset {uname, owner, dataset_name}: {e}")

        if order_by == 'modified_on':
            sort_key = lambda tup: cache_controller.cached_modified_on(tup)
            sorted_ids = sorted(safe_ids, key=sort_key)
        elif order_by == 'created_on':
            sort_key = lambda tup: cache_controller.cached_created_time(tup)
            sorted_ids = sorted(safe_ids, key=sort_key)
        else:
            sorted_ids = natsorted(safe_ids, key=lambda elt: elt[2])

        if reverse:
            sorted_ids.reverse()

        edges = [(tup[1], tup[2]) for tup in sorted_ids]
        cursors = [base64.b64encode("{}".format(cnt).encode("UTF-8")).decode("UTF-8") for cnt, x in enumerate(edges)]
        lbc = ListBasedConnection(edges, cursors, kwargs)
        lbc.apply()

        # Get Dataset instances
        edge_objs = []
        for edge, cursor in zip(lbc.edges, lbc.cursors):
            create_data = {"id": "{}&{}".format(edge[0], edge[1]),
                           "name": edge[1],
                           "owner": edge[0]}

            edge_objs.append(DatasetConnection.Edge(node=Dataset(**create_data),
                                                    cursor=cursor))

        dc = DatasetConnection(edges=edge_objs, page_info=lbc.page_info)
        logger.info(f"Listed datasets in {time.time()-t0:.2f}sec")
        return dc

    def resolve_remote_datasets(self, info, order_by: str, sort: str, **kwargs):
        """Method to return a all RemoteDataset instances for the logged in user

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
        ... on Dataset{
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
            raise IOError(f"Failed to retrieve Dataset listing from remote server: {response.json()}")
        response_data = response.json()
        if 'errors' in response_data:
            raise IOError(f"Failed to retrieve Dataset listing from remote server: {response_data['errors']}")

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
                                "import_url": f"https://{remote_url}/{node['namespace']}/{node['repositoryName']}.git/"
                               }

                edge_objs.append(RemoteDatasetConnection.Edge(node=RemoteDataset(**create_data),
                                                              cursor=edge['cursor']))

        # Create Page Info instance
        page_info_data = response_data['data']['repositories']['pageInfo']
        page_info = graphene.relay.PageInfo(has_next_page=page_info_data['hasNextPage'],
                                            has_previous_page=page_info_data['hasPreviousPage'],
                                            start_cursor=page_info_data['startCursor'],
                                            end_cursor=page_info_data['endCursor'])

        return RemoteDatasetConnection(edges=edge_objs, page_info=page_info)
