# -*- coding: utf-8 -*-
# snapshottest: v1 - https://goo.gl/zC4yUc
from __future__ import unicode_literals

from snapshottest import Snapshot


snapshots = Snapshot()

snapshots['TestDatasetMutations.test_create_dataset 1'] = {
    'data': {
        'createDataset': {
            'dataset': {
                'datasetType': {
                    'description': 'Dataset storage provided by your Gigantum account supporting files up to 5GB in size',
                    'id': 'RGF0YXNldFR5cGU6Z2lnYW50dW1fb2JqZWN0X3Yx',
                    'name': 'Gigantum Cloud'
                },
                'description': 'my test dataset',
                'id': 'RGF0YXNldDpkZWZhdWx0JnRlc3QtZGF0YXNldC0x',
                'name': 'test-dataset-1',
                'schemaVersion': 2
            }
        }
    }
}

snapshots['TestDatasetMutations.test_create_dataset 2'] = {
    'data': {
        'dataset': {
            'datasetType': {
                'description': 'Dataset storage provided by your Gigantum account supporting files up to 5GB in size',
                'id': 'RGF0YXNldFR5cGU6Z2lnYW50dW1fb2JqZWN0X3Yx',
                'name': 'Gigantum Cloud'
            },
            'description': 'my test dataset',
            'id': 'RGF0YXNldDpkZWZhdWx0JnRlc3QtZGF0YXNldC0x',
            'name': 'test-dataset-1',
            'schemaVersion': 2
        }
    }
}

snapshots['TestDatasetMutations.test_modify_dataset_link 1'] = {
    'data': {
        'modifyDatasetLink': {
            'newLabbookEdge': {
                'node': {
                    'description': 'testing dataset links',
                    'id': 'TGFiYm9vazpkZWZhdWx0JnRlc3QtbGI=',
                    'linkedDatasets': [
                        {
                            'name': 'dataset100'
                        }
                    ],
                    'name': 'test-lb'
                }
            }
        }
    }
}

snapshots['TestDatasetMutations.test_modify_dataset_link 2'] = {
    'data': {
        'modifyDatasetLink': {
            'newLabbookEdge': {
                'node': {
                    'description': 'testing dataset links',
                    'id': 'TGFiYm9vazpkZWZhdWx0JnRlc3QtbGI=',
                    'linkedDatasets': [
                    ],
                    'name': 'test-lb'
                }
            }
        }
    }
}

snapshots['TestDatasetMutations.test_modify_dataset_link_errors 1'] = {
    'data': {
        'modifyDatasetLink': None
    },
    'errors': [
        {
            'locations': [
                {
                    'column': 22,
                    'line': 4
                }
            ],
            'message': 'Unsupported action. Use `link`, `unlink`, or `update`',
            'path': [
                'modifyDatasetLink'
            ]
        }
    ]
}

snapshots['TestDatasetMutations.test_configure_local 1'] = {
    'data': {
        'dataset': {
            'backendConfiguration': [
                {
                    'description': 'A directory in <gigantum_working_dir>/local_data/ to use as the dataset source',
                    'parameter': 'Data Directory',
                    'parameterType': 'str',
                    'value': None
                }
            ],
            'backendIsConfigured': False
        }
    }
}

snapshots['TestDatasetMutations.test_configure_local 2'] = {
    'data': {
        'configureDataset': {
            'backgroundJobKey': None,
            'confirmMessage': None,
            'errorMessage': 'Data Directory does not exist.',
            'hasBackgroundJob': True,
            'isConfigured': False,
            'shouldConfirm': False
        }
    }
}

snapshots['TestDatasetMutations.test_configure_local 3'] = {
    'data': {
        'configureDataset': {
            'backgroundJobKey': None,
            'confirmMessage': None,
            'errorMessage': None,
            'hasBackgroundJob': True,
            'isConfigured': True,
            'shouldConfirm': False
        }
    }
}

snapshots['TestDatasetMutations.test_update_dataset_link 1'] = {
    'data': {
        'modifyDatasetLink': {
            'newLabbookEdge': {
                'node': {
                    'description': 'testing dataset links',
                    'id': 'TGFiYm9vazpkZWZhdWx0JnRlc3QtbGI=',
                    'linkedDatasets': [
                        {
                            'name': 'dataset100'
                        }
                    ],
                    'name': 'test-lb'
                }
            }
        }
    }
}

snapshots['TestDatasetMutations.test_update_dataset_link 2'] = {
    'data': {
        'modifyDatasetLink': {
            'newLabbookEdge': {
                'node': {
                    'description': 'testing dataset links',
                    'id': 'TGFiYm9vazpkZWZhdWx0JnRlc3QtbGI=',
                    'linkedDatasets': [
                        {
                            'name': 'dataset100'
                        }
                    ],
                    'name': 'test-lb'
                }
            }
        }
    }
}
