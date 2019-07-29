import os
import json
import pprint
import logging
import base64
from typing import List, Tuple

from sgqlc.endpoint.http import HTTPEndpoint


def get_default_host():
    return 'http://localhost:10000/api/labbook/'


class GraphQLException(Exception):
    pass


def query(query_str, variables=None):
    if not os.environ.get('ID_TOKEN'):
        raise GraphQLException('ID_TOKEN not found or not set')

    if not os.environ.get('ACCESS_TOKEN'):
        raise GraphQLException('ACCESS_TOKEN not found or not set')

    headers = {
        'Identity': os.environ['ID_TOKEN'],
        'Authorization': f'Bearer {os.environ["ACCESS_TOKEN"]}'
    }
    endpt = HTTPEndpoint(get_default_host(), base_headers=headers, method='POST')
    response = endpt(query_str, variables or {})

    if 'errors' in response:
        raise GraphQLException(json.dumps(response))

    return response


def create_py3_minimal_project(name: str):

    all_bases_query = """
    {
        availableBases {
            edges {
                node {
                    schema
                    repository
                    componentId
                    revision
                    name
                    description
                }
            }
        }
    }
    """
    results = query(all_bases_query, {})

    build_vars = {'labbookName': name}
    for base_option in results['data']['availableBases']['edges']:
        if base_option['node']['componentId'] == 'python3-minimal':
            build_vars['componentId'] = base_option['node']['componentId']
            build_vars['baseId'] = base_option['node']['componentId']
            build_vars['repository'] = base_option['node']['repository']
            build_vars['revision'] = base_option['node']['revision']
            build_vars['schema'] = base_option['node']['schema']
            break
    else:
        raise GraphQLException('Cannot find python3 minimal base!')

    create_project_query = """
    mutation createProject($labbookName: String!,
                           $baseId: String!, $revision: Int!,
                           $repository: String!) {
        createLabbook(input: {
            name: $labbookName,
            description: "Project created via GraphQL CLI mutation in test harness.",
            baseId: $baseId,
            revision: $revision,
            repository: $repository
        }) {
            labbook {
                owner
                name
            }
        }
    }
    """
    create_project_results = query(create_project_query, build_vars)
    pprint.pprint(create_project_results)
    return create_project_results['data']['createLabbook']['labbook']['owner'], \
           create_project_results['data']['createLabbook']['labbook']['name']


def list_remote_projects() -> List[Tuple[str, str]]:
    labbook_list_query = """
    {
        labbookList {
            remoteLabbooks(first: 2000) {
                edges {
                    node {
                        owner
                        name
                    }
                }
            }
        }
    }
    """

    results = query(labbook_list_query, {})

    if 'errors' in results:
        raise GraphQLException(json.dumps(results))

    return [(r['node']['owner'], r['node']['name'])
            for r in results['data']['labbookList']['remoteLabbooks']['edges']]


def list_remote_datasets() -> List[Tuple[str, str]]:
    labbook_list_query = """
    {
        datasetList {
            remoteDatasets(first: 2000) {
                edges {
                    node {
                        owner
                        name
                    }
                }
            }
        }
    }
    """

    results = query(labbook_list_query, {})

    if 'errors' in results:
        raise GraphQLException(json.dumps(results))

    return [(r['node']['owner'], r['node']['name'])
            for r in results['data']['datasetList']['remoteDatasets']['edges']]


def list_local_projects():
    labbook_list_query = """
    {
        labbookList {
            localLabbooks(first: 2000) {
                edges {
                    node {
                        owner
                        name
                    }
                }
            }
        }
    }
    """
    results = query(labbook_list_query, {})
    if 'errors' in results:
        raise GraphQLException(json.dumps(results))

    pprint.pprint(results)
    return [(r['node']['owner'], r['node']['name'])
            for r in results['data']['labbookList']['localLabbooks']['edges']]


def delete_remote_project(owner_name, project_name):
    logging.info(f'Delete remote project {owner_name}/{project_name}')
    delete_remote_query = """
    mutation deleteRemoteProject($owner: String!, $name: String!) {
        deleteRemoteLabbook(input: {
            owner: $owner,
            labbookName: $name,
            confirm: true
        }) {
            success
        }
    }
    """
    var = {'owner': owner_name, 'name': project_name}
    result = query(delete_remote_query, var)

    if 'errors' in result:
        raise GraphQLException(json.dumps(result))


def delete_dataset(owner_name, project_name, delete_local=True, delete_remote=True):
    mutation = 'mutation'

    if os.environ['GIGANTUM_USERNAME'] != owner_name:
        logging.info(f"Cannot delete a remote dataset {os.environ['GIGANTUM_USERNAME']} "
                     f"does not own.")
        delete_remote = False
    logging.info(f'Delete dataset {owner_name}/{project_name} '
                 f'local={delete_local}, remote={delete_remote}')
    delete_remote_query = """
    mutation deleteDataset($owner: String!, $name: String!,
                                 $local: Boolean!, $remote: Boolean!, $clientMutationId: String! ) {
        deleteDataset(input: {
            owner: $owner,
            datasetName: $name,
            local: $local,
            remote: $remote
            clientMutationId: $clientMutationId
        }) {
            localDeleted
            remoteDeleted
            clientMutationId
        }
    }
    """
    var = {'owner': owner_name, 'name': project_name, 'local': delete_local,
           'remote': delete_remote,'clientMutationId':mutation}
    result = query(delete_remote_query, var)

    if 'errors' in result:
        raise GraphQLException(json.dumps(result))


def delete_local_project(owner_name, project_name):
    logging.info(f'Delete local project {owner_name}/{project_name}')
    delete_local_query = """
    mutation deleteLocalProject($owner: String!, $name: String!) {
        deleteLabbook(input: {
            owner: $owner,
            labbookName: $name,
            confirm: true
        }) {
            success
        }
    }
    """
    var = {'owner': owner_name, 'name': project_name}
    result = query(delete_local_query, var)

    if 'errors' in result:
        raise GraphQLException(json.dumps(result))

    return result['data']['deleteLabbook']['success']


def publish_project(owner_name, project_name):
    logging.info(f'Publishing {owner_name}/{project_name}')
    publish_query = """
    mutation publish($owner: String!,
                     $name: String!,
                     $setPublic: Boolean) {
        publishLabbook(input: {
            owner: $owner,
            labbookName: $name,
            setPublic: $setPublic
        }) {
            jobKey
        }
    }
    """

    var = {'owner': owner_name, 'name': project_name, 'setPublic': False}
    job_key_result = query(publish_query, var)

    if 'errors' in job_key_result:
        raise GraphQLException(json.dumps(job_key_result))

