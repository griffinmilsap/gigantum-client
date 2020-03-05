# -*- coding: utf-8 -*-
# snapshottest: v1 - https://goo.gl/zC4yUc
from __future__ import unicode_literals

from snapshottest import Snapshot


snapshots = Snapshot()

snapshots['TestLabBookServiceMutations.test_makedir 1'] = {
    'data': {
        'makeLabbookDirectory': {
            'newLabbookFileEdge': {
                'node': {
                    'isDir': True,
                    'key': 'new_folder/',
                    'size': '0'
                }
            }
        }
    }
}

snapshots['TestLabBookServiceMutations.test_create_labbook 1'] = {
    'data': {
        'createLabbook': {
            'labbook': {
                'description': 'my test description',
                'id': 'TGFiYm9vazpkZWZhdWx0JnRlc3QtbGFiLWJvb2sx',
                'name': 'test-lab-book1'
            }
        }
    }
}

snapshots['TestLabBookServiceMutations.test_create_labbook_already_exists 1'] = {
    'data': {
        'createLabbook': {
            'labbook': {
                'description': 'my test description',
                'id': 'TGFiYm9vazpkZWZhdWx0JnRlc3QtbGFiLWR1cGxpY2F0ZQ==',
                'name': 'test-lab-duplicate'
            }
        }
    }
}

snapshots['TestLabBookServiceMutations.test_create_labbook_already_exists 2'] = {
    'data': {
        'labbook': {
            'description': 'my test description',
            'name': 'test-lab-duplicate'
        }
    }
}

snapshots['TestLabBookServiceMutations.test_create_labbook_already_exists 3'] = {
    'data': {
        'createLabbook': None
    },
    'errors': [
        {
            'locations': [
                {
                    'column': 11,
                    'line': 4
                }
            ],
            'message': 'LabBook `test-lab-duplicate` already exists locally. Choose a new LabBook name',
            'path': [
                'createLabbook'
            ]
        }
    ]
}

snapshots['TestLabBookServiceMutations.test_create_labbook 2'] = {
    'data': {
        'labbook': {
            'activityRecords': {
                'edges': [
                    {
                        'node': {
                            'detailObjects': [
                                {
                                    'data': [
                                        [
                                            'text/plain',
                                            '''Added base quickstart-jupyterlab

Data Science Quickstart using Jupyterlab, numpy, and Matplotlib. A great base for any analysis.

  - repository: gigantum_base-images-testing
  - component: quickstart-jupyterlab
  - revision: 2
'''
                                        ]
                                    ],
                                    'importance': 0,
                                    'show': False,
                                    'tags': [
                                    ],
                                    'type': 'ENVIRONMENT'
                                }
                            ],
                            'email': 'jane@doe.com',
                            'importance': 0,
                            'message': 'Added base: quickstart-jupyterlab r2',
                            'show': True,
                            'tags': [
                                'environment',
                                'base'
                            ],
                            'type': 'ENVIRONMENT',
                            'username': 'default'
                        }
                    },
                    {
                        'node': {
                            'detailObjects': [
                                {
                                    'data': [
                                        [
                                            'text/plain',
                                            'Add pip3 managed package: numpy "1.14.0"'
                                        ]
                                    ],
                                    'importance': 0,
                                    'show': False,
                                    'tags': [
                                    ],
                                    'type': 'ENVIRONMENT'
                                },
                                {
                                    'data': [
                                        [
                                            'text/plain',
                                            'Add pip3 managed package: matplotlib "2.1.1"'
                                        ]
                                    ],
                                    'importance': 0,
                                    'show': False,
                                    'tags': [
                                    ],
                                    'type': 'ENVIRONMENT'
                                },
                                {
                                    'data': [
                                        [
                                            'text/plain',
                                            'Add pip3 managed package: jupyter "1.0.0"'
                                        ]
                                    ],
                                    'importance': 0,
                                    'show': False,
                                    'tags': [
                                    ],
                                    'type': 'ENVIRONMENT'
                                },
                                {
                                    'data': [
                                        [
                                            'text/plain',
                                            'Add pip3 managed package: jupyterlab "0.31.1"'
                                        ]
                                    ],
                                    'importance': 0,
                                    'show': False,
                                    'tags': [
                                    ],
                                    'type': 'ENVIRONMENT'
                                },
                                {
                                    'data': [
                                        [
                                            'text/plain',
                                            'Add pip3 managed package: ipywidgets "7.1.0"'
                                        ]
                                    ],
                                    'importance': 0,
                                    'show': False,
                                    'tags': [
                                    ],
                                    'type': 'ENVIRONMENT'
                                },
                                {
                                    'data': [
                                        [
                                            'text/plain',
                                            'Add pip3 managed package: pandas "0.22.0"'
                                        ]
                                    ],
                                    'importance': 0,
                                    'show': False,
                                    'tags': [
                                    ],
                                    'type': 'ENVIRONMENT'
                                }
                            ],
                            'email': 'jane@doe.com',
                            'importance': 0,
                            'message': 'Added 6 pip3 package(s). ',
                            'show': True,
                            'tags': [
                                'environment',
                                'package_manager',
                                'pip3'
                            ],
                            'type': 'ENVIRONMENT',
                            'username': 'default'
                        }
                    },
                    {
                        'node': {
                            'detailObjects': [
                                {
                                    'data': [
                                        [
                                            'text/plain',
                                            'Add apt managed package: vim "2:7.4.1689-3ubuntu1.2"'
                                        ]
                                    ],
                                    'importance': 0,
                                    'show': False,
                                    'tags': [
                                    ],
                                    'type': 'ENVIRONMENT'
                                }
                            ],
                            'email': 'jane@doe.com',
                            'importance': 0,
                            'message': 'Added 1 apt package(s). ',
                            'show': True,
                            'tags': [
                                'environment',
                                'package_manager',
                                'apt'
                            ],
                            'type': 'ENVIRONMENT',
                            'username': 'default'
                        }
                    },
                    {
                        'node': {
                            'detailObjects': [
                                {
                                    'data': [
                                        [
                                            'text/plain',
                                            'Created new Project: default/test-lab-book1'
                                        ]
                                    ],
                                    'importance': 0,
                                    'show': False,
                                    'tags': [
                                    ],
                                    'type': 'LABBOOK'
                                }
                            ],
                            'email': 'jane@doe.com',
                            'importance': 255,
                            'message': 'Created new Project: default/test-lab-book1',
                            'show': True,
                            'tags': [
                            ],
                            'type': 'LABBOOK',
                            'username': 'default'
                        }
                    }
                ]
            }
        }
    }
}

snapshots['TestLabBookServiceMutations.test_write_readme 1'] = {
    'data': {
        'writeLabbookReadme': {
            'updatedLabbook': {
                'description': 'Cats labbook 1',
                'name': 'labbook1',
                'overview': {
                    'readme': '''##Overview

This is my readme
 :df,a//3p49kasdf'''
                }
            }
        }
    }
}
