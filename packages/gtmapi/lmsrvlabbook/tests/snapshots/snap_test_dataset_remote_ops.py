# -*- coding: utf-8 -*-
# snapshottest: v1 - https://goo.gl/zC4yUc
from __future__ import unicode_literals

from snapshottest import Snapshot


snapshots = Snapshot()

snapshots['TestDatasetRemoteOperations.test_list_remote_datasets_az 1'] = {
    'data': {
        'datasetList': {
            'remoteDatasets': {
                'edges': [
                    {
                        'cursor': 'MTow',
                        'node': {
                            'creationDateUtc': '2019-06-05T01:06:06.760185Z',
                            'description': 'my test project',
                            'id': 'UmVtb3RlRGF0YXNldDpkZW1vLXVzZXImdGVzdC1wdWJsaXNoLW1heS00',
                            'isLocal': False,
                            'modifiedDateUtc': '2019-09-12T15:35:11.664Z',
                            'name': 'test-publish-may-4',
                            'owner': 'demo-user',
                            "importUrl": "https://repo.gigantum.io/demo-user/test-publish-may-4.git/"
                        }
                    },
                    {
                        'cursor': 'MTox',
                        'node': {
                            'creationDateUtc': '2019-07-22T11:06:37.435584Z',
                            'description': 'Testing public project visibility.',
                            'id': 'UmVtb3RlRGF0YXNldDpkZW1vLXVzZXImdGVzdC1wdWJsaWMtcHJvamVjdA==',
                            'isLocal': False,
                            'modifiedDateUtc': '2019-09-12T15:17:23.414Z',
                            'name': 'test-public-project',
                            'owner': 'demo-user',
                            "importUrl": "https://repo.gigantum.io/demo-user/test-public-project.git/"
                        }
                    }
                ],
                'pageInfo': {
                    'endCursor': 'MTox',
                    'hasNextPage': True,
                    'hasPreviousPage': False,
                    'startCursor': 'MTow'
                }
            }
        }
    }
}

snapshots['TestDatasetRemoteOperations.test_list_remote_datasets_az 2'] = {
    'data': {
        'datasetList': {
            'remoteDatasets': {
                'edges': [
                    {
                        'cursor': 'MTox',
                        'node': {
                            'creationDateUtc': '2019-08-28T15:09:22.506423Z',
                            'description': 'another project',
                            'id': 'UmVtb3RlRGF0YXNldDpkZW1vLXVzZXImenotcHJvamVjdA==',
                            'modifiedDateUtc': '2019-08-28T15:09:37.449Z',
                            'name': 'zz-project',
                            'owner': 'demo-user'
                        }
                    }
                ],
                'pageInfo': {
                    'hasNextPage': True
                }
            }
        }
    }
}

snapshots['TestDatasetRemoteOperations.test_list_remote_datasets_modified 1'] = {
    'data': {
        'datasetList': {
            'remoteDatasets': {
                'edges': [
                    {
                        'cursor': 'MTow',
                        'node': {
                            'creationDateUtc': '2019-09-26T20:17:17.134888Z',
                            'description': 'gdhjgfhj',
                            'id': 'UmVtb3RlRGF0YXNldDpkZW1vLXVzZXImZ2Zoamdoag==',
                            'isLocal': False,
                            'modifiedDateUtc': '2019-09-26T20:17:39.054Z',
                            'name': 'gfhjghj',
                            'owner': 'demo-user'
                        }
                    },
                    {
                        'cursor': 'MTox',
                        'node': {
                            'creationDateUtc': '2019-09-10T19:43:24.086835Z',
                            'description': 'My description',
                            'id': 'UmVtb3RlRGF0YXNldDpkZW1vLXVzZXImcHJpdmF0ZS1wcm9qZWN0',
                            'isLocal': False,
                            'modifiedDateUtc': '2019-09-21T01:05:55.758Z',
                            'name': 'private-project',
                            'owner': 'demo-user'
                        }
                    }
                ],
                'pageInfo': {
                    'endCursor': 'MTox',
                    'hasNextPage': True,
                    'hasPreviousPage': False,
                    'startCursor': 'MTow'
                }
            }
        }
    }
}

snapshots['TestDatasetRemoteOperations.test_list_remote_datasets_modified 2'] = {
    'data': {
        'datasetList': {
            'remoteDatasets': {
                'edges': [
                    {
                        'cursor': 'MTow',
                        'node': {
                            'creationDateUtc': '2019-02-28T01:51:33.471998Z',
                            'description': 'sdfgsdfg',
                            'id': 'UmVtb3RlRGF0YXNldDpkbWsmdGVzdGluZy1kcy1zeW5j',
                            'modifiedDateUtc': '2019-02-28T01:54:02.369Z',
                            'name': 'testing-ds-sync',
                            'owner': 'dmk'
                        }
                    },
                    {
                        'cursor': 'MTox',
                        'node': {
                            'creationDateUtc': '2019-03-02T15:25:09.664239Z',
                            'description': 'sdfasdfasdfsadf',
                            'id': 'UmVtb3RlRGF0YXNldDpkZW1vLXVzZXImdGVzdC1hY3Rpdml0eQ==',
                            'modifiedDateUtc': '2019-03-04T15:00:32.280Z',
                            'name': 'test-activity',
                            'owner': 'demo-user'
                        }
                    },
                    {
                        'cursor': 'MToz',
                        'node': {
                            'creationDateUtc': '2019-03-05T04:17:31.618460Z',
                            'description': 'asdfasdf',
                            'id': 'UmVtb3RlRGF0YXNldDpkZW1vLXVzZXImdGVzdC1saW5r',
                            'modifiedDateUtc': '2019-03-05T04:19:05.973Z',
                            'name': 'test-link',
                            'owner': 'demo-user'
                        }
                    },
                    {
                        'cursor': 'MTo1',
                        'node': {
                            'creationDateUtc': '2019-03-05T17:43:12.025266Z',
                            'description': 'This is a demo project',
                            'id': 'UmVtb3RlRGF0YXNldDpkZW1vLXVzZXImbXktbmV3LXByb2plY3QtdGhpbmc=',
                            'modifiedDateUtc': '2019-03-05T18:41:30.188Z',
                            'name': 'my-new-project-thing',
                            'owner': 'demo-user'
                        }
                    },
                    {
                        'cursor': 'MTo2',
                        'node': {
                            'creationDateUtc': '2019-08-28T15:09:22.506423Z',
                            'description': 'ggjkdhjfh',
                            'id': 'UmVtb3RlRGF0YXNldDpkZW1vLXVzZXImYXByb2o=',
                            'modifiedDateUtc': '2019-08-28T15:09:37.449Z',
                            'name': 'aproj',
                            'owner': 'demo-user'
                        }
                    }
                ],
                'pageInfo': {
                    'endCursor': 'MTo4',
                    'hasNextPage': False,
                    'hasPreviousPage': False,
                    'startCursor': 'MTow'
                }
            }
        }
    }
}

snapshots['TestDatasetRemoteOperations.test_list_remote_datasets_page 1'] = {
    'data': {
        'datasetList': {
            'remoteDatasets': {
                'edges': [
                    {
                        'cursor': 'MTow',
                        'node': {
                            'creationDateUtc': '2019-06-05T01:06:06.760185Z',
                            'description': '',
                            'id': 'UmVtb3RlRGF0YXNldDpkZW1vLXVzZXImdGVzdC1wdWJsaXNoLW1heS00',
                            'isLocal': False,
                            'modifiedDateUtc': '2019-09-12T15:35:11.664Z',
                            'name': 'test-publish-may-4',
                            'owner': 'demo-user'
                        }
                    }
                ],
                'pageInfo': {
                    'endCursor': 'MTow',
                    'hasNextPage': True,
                    'hasPreviousPage': False,
                    'startCursor': 'MTow'
                }
            }
        }
    }
}

snapshots['TestDatasetRemoteOperations.test_list_remote_datasets_page 2'] = {
    'data': {
        'datasetList': {
            'remoteDatasets': {
                'edges': [
                    {
                        'cursor': 'Mjow',
                        'node': {
                            'creationDateUtc': '2019-02-28T01:51:33.471998Z',
                            'description': 'sdfgsdfg',
                            'id': 'UmVtb3RlRGF0YXNldDpkbWsmdGVzdGluZy1kcy1zeW5j',
                            'modifiedDateUtc': '2019-02-28T01:54:02.369Z',
                            'name': 'testing-ds-sync',
                            'owner': 'dmk'
                        }
                    },
                    {
                        'cursor': 'Mjoz',
                        'node': {
                            'creationDateUtc': '2019-03-02T15:25:09.664239Z',
                            'description': 'sdfasdfasdfsadf',
                            'id': 'UmVtb3RlRGF0YXNldDpkZW1vLXVzZXImdGVzdC1hY3Rpdml0eQ==',
                            'modifiedDateUtc': '2019-03-04T15:00:32.280Z',
                            'name': 'test-activity',
                            'owner': 'demo-user'
                        }
                    }
                ],
                'pageInfo': {
                    'endCursor': 'Mjoz',
                    'hasNextPage': False,
                    'hasPreviousPage': False,
                    'startCursor': 'Mjow'
                }
            }
        }
    }
}
