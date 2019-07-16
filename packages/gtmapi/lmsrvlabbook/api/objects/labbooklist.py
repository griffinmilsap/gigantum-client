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
import time
import base64
import graphene
import requests
import flask
from typing import Any, Optional, Tuple

from gtmcore.logging import LMLogger
from gtmcore.inventory.inventory import InventoryManager
from gtmcore.configuration import Configuration

from lmsrvcore.caching import RepoCacheController
from lmsrvcore.auth.user import get_logged_in_username
from lmsrvcore.api.connections import ListBasedConnection
from lmsrvcore.auth.identity import parse_token

from lmsrvlabbook.api.connections.labbook import LabbookConnection, Labbook
from lmsrvlabbook.api.connections.remotelabbook import RemoteLabbookConnection, RemoteLabbook

logger = LMLogger.get_logger()


class LabbookList(graphene.ObjectType, interfaces=(graphene.relay.Node,)):
    """A type simply used as a container to group local and remote LabBooks for better relay support

    Labbook and RemoteLabbook objects are uniquely identified by both the "owner" and the "name" of the LabBook

    NOTE: RemoteLabbooks require all fields to be explicitly set as there is no current way to asynchronously retrieve
          the data
    """
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
        tSTART = time.time()
        username = get_logged_in_username()

        if sort == "desc":
            reverse = True
        elif sort == "asc":
            reverse = False
        else:
            raise ValueError(f"Unsupported sort_str: {sort}. Use `desc`, `asc`")

        # Collect all labbooks for all owners
        inv_manager = InventoryManager()
        #local_lbs = inv_manager.list_labbooks(username=username) #, sort_mode=order_by)

        logger.warning(f"Listed LBs after {time.time()-tSTART:.2f}")

        r = RepoCacheController()
        ids = inv_manager.list_repository_ids(username, 'labbook')

        safe_ids = []
        for (uname, owner, project_name) in ids:
            try:
                r.cached_modified_on((username, owner, project_name))
                r.cached_created_time((username, owner, project_name))
                safe_ids.append((uname, owner, project_name))
            except Exception as e:
                logger.warning(f"Error loading LabBook {uname, owner, project_name}: {e}")

        logger.warning(f"Ran safe LBs after {time.time()-tSTART:.2f}sec")

        if order_by == 'modified_on':
            sort_key = lambda tup: r.cached_modified_on(tup)
        elif order_by == 'created_on':
            sort_key = lambda tup: r.cached_created_time(tup)
        else:
            sort_key = lambda tup: tup[2]

        sorted_ids = sorted(safe_ids, key=sort_key)
        if reverse:
            sorted_ids.reverse()
        logger.warning(f"Sorted all safe LBs after {time.time()-tSTART:.2f}sec")

        edges = [(tup[1], tup[2]) for tup in sorted_ids]
        cursors = [base64.b64encode("{}".format(cnt).encode("UTF-8")).decode("UTF-8") for cnt, x in enumerate(edges)]

        # Process slicing and cursor args
        lbc = ListBasedConnection(edges, cursors, kwargs)
        lbc.apply()

        # Get Labbook instances
        edge_objs = []
        for edge, cursor in zip(lbc.edges, lbc.cursors):
            create_data = {"id": "{}&{}".format(edge[0], edge[1]),
                           "name": edge[1],
                           "owner": edge[0]}

            edge_objs.append(LabbookConnection.Edge(node=Labbook(**create_data),
                                                    cursor=cursor))

        logger.warning(f"Returning from mutation after {time.time()-tSTART:.2f}sec")
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
        # Load config data
        configuration = Configuration().config

        # Extract valid Bearer token
        token = None
        if hasattr(info.context.headers, 'environ'):
            if "HTTP_AUTHORIZATION" in info.context.headers.environ:
                token = parse_token(info.context.headers.environ["HTTP_AUTHORIZATION"])
        if not token:
            raise ValueError("Authorization header not provided. Cannot list remote LabBooks.")

        # Get remote server configuration
        default_remote = configuration['git']['default_remote']
        index_service = None
        for remote in configuration['git']['remotes']:
            if default_remote == remote:
                index_service = configuration['git']['remotes'][remote]['index_service']
                break

        if not index_service:
            raise ValueError('index_service could not be found')

        # Prep arguments
        if "first" in kwargs:
            per_page = int(kwargs['first'])
        elif "last" in kwargs:
            raise ValueError("Cannot page in reverse direction, must provide first/after parameters instead")
        else:
            per_page = 20

        # use version=2 to page through both projects and datasets returned by gitlab but only return projects.
        # omitting the version parameter will return projects and datasets together, but avoids breaking functionality
        # in any gigantum instances not using the latest client code
        url = f"https://{index_service}/projects?version=2&first={per_page}"

        # Add optional arguments
        if kwargs.get("after"):
            url = f"{url}&after={kwargs.get('after')}"
        elif kwargs.get("before"):
            raise ValueError("Cannot page in reverse direction, must provide first/after parameters instead")

        if order_by is not None:
            if order_by not in ['name', 'created_on', 'modified_on']:
                raise ValueError(f"Unsupported order_by: {order_by}. Use `name`, `created_on`, `modified_on`")
            url = f"{url}&order_by={order_by}"

        if sort is not None:
            if sort not in ['desc', 'asc']:
                raise ValueError(f"Unsupported sort: {sort}. Use `desc`, `asc`")
            url = f"{url}&sort={sort}"

        # Query SaaS index service for data
        access_token = flask.g.get('access_token', None)
        id_token = flask.g.get('id_token', None)
        response = requests.get(url, headers={"Authorization": f"Bearer {access_token}",
                                              "Identity": id_token})

        if response.status_code != 200:
            raise IOError("Failed to retrieve Project listing from remote server")
        edges = response.json()

        # Get Labbook instances
        edge_objs = []
        for edge in edges:
            create_data = {"id": "{}&{}".format(edge["namespace"], edge["project"]),
                           "name": edge["project"],
                           "owner": edge["namespace"],
                           "description": edge["description"],
                           "creation_date_utc": edge["created_at"],
                           "modified_date_utc": edge["modified_at"],
                           "visibility": "public" if edge.get("visibility") == "public_project" else "private"}

            edge_objs.append(RemoteLabbookConnection.Edge(node=RemoteLabbook(**create_data),
                                                          cursor=edge['cursor']))

        # Create Page Info instance
        has_previous_page = True if kwargs.get("after") else False
        has_next_page = len(edges) == per_page

        page_info = graphene.relay.PageInfo(has_next_page=has_next_page, has_previous_page=has_previous_page,
                                            start_cursor=edges[0]['cursor'] if edges else None,
                                            end_cursor=edges[-1]['cursor'] if edges else None)

        return RemoteLabbookConnection(edges=edge_objs, page_info=page_info)
