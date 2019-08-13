# -*- coding: utf-8 -*-
# snapshottest: v1 - https://goo.gl/zC4yUc
from __future__ import unicode_literals

from snapshottest import Snapshot


snapshots = Snapshot()

snapshots['TestEnvironmentServiceQueries.test_get_environment_status 1'] = {
    'data': {
        'labbook': {
            'environment': {
                'containerStatus': 'NOT_RUNNING',
                'imageStatus': 'DOES_NOT_EXIST'
            }
        }
    }
}

snapshots['TestEnvironmentServiceQueries.test_get_base 1'] = {
    'data': {
        'createLabbook': {
            'labbook': {
                'description': 'my test 1',
                'id': 'TGFiYm9vazpkZWZhdWx0JmxhYmJvb2stYmFzZS10ZXN0',
                'name': 'labbook-base-test'
            }
        }
    }
}

snapshots['TestEnvironmentServiceQueries.test_get_base 2'] = {
    'data': {
        'labbook': {
            'description': 'my test 1',
            'environment': {
                'base': {
                    'componentId': 'quickstart-jupyterlab',
                    'description': 'Data Science Quickstart using Jupyterlab, numpy, and Matplotlib. A great base for any analysis.',
                    'developmentTools': [
                        'jupyterlab'
                    ],
                    'dockerImageNamespace': 'gigantum',
                    'dockerImageRepository': 'python3-minimal',
                    'dockerImageServer': 'hub.docker.com',
                    'dockerImageTag': '1effaaea-2018-05-23',
                    'icon': 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=',
                    'id': 'QmFzZUNvbXBvbmVudDpnaWdhbnR1bV9iYXNlLWltYWdlcy10ZXN0aW5nJnF1aWNrc3RhcnQtanVweXRlcmxhYiYy',
                    'languages': [
                        'python3'
                    ],
                    'license': 'MIT',
                    'name': 'Data Science Quickstart with JupyterLab',
                    'osClass': 'ubuntu',
                    'osRelease': '18.04',
                    'packageManagers': [
                        'apt',
                        'pip3'
                    ],
                    'readme': 'Empty for now',
                    'tags': [
                        'ubuntu',
                        'python3',
                        'jupyterlab'
                    ],
                    'url': None
                }
            },
            'name': 'labbook-base-test'
        }
    }
}

snapshots['TestEnvironmentServiceQueries.test_package_query 1'] = {
    'data': {
        'labbook': {
            'checkPackages': [
                {
                    'id': 'UGFja2FnZUNvbXBvbmVudDpwaXAmZ3RtdW5pdDEmMC4yLjQ=',
                    'isValid': True,
                    'manager': 'pip',
                    'package': 'gtmunit1',
                    'version': '0.2.4'
                },
                {
                    'id': 'UGFja2FnZUNvbXBvbmVudDpwaXAmZ3RtdW5pdDImMTIuMg==',
                    'isValid': True,
                    'manager': 'pip',
                    'package': 'gtmunit2',
                    'version': '12.2'
                }
            ],
            'id': 'TGFiYm9vazpkZWZhdWx0JmxhYmJvb2s2'
        }
    }
}

snapshots['TestEnvironmentServiceQueries.test_get_package_manager 1'] = {
    'data': {
        'labbook': {
            'environment': {
                'packageDependencies': {
                    'edges': [
                    ],
                    'pageInfo': {
                        'hasNextPage': False
                    }
                }
            }
        }
    }
}

snapshots['TestEnvironmentServiceQueries.test_get_package_manager 2'] = {
    'data': {
        'labbook': {
            'environment': {
                'packageDependencies': {
                    'edges': [
                        {
                            'cursor': 'MA==',
                            'node': {
                                'fromBase': False,
                                'id': 'UGFja2FnZUNvbXBvbmVudDphcHQmbHhtbCYzLjQ=',
                                'manager': 'apt',
                                'package': 'lxml',
                                'version': '3.4'
                            }
                        },
                        {
                            'cursor': 'MQ==',
                            'node': {
                                'fromBase': False,
                                'id': 'UGFja2FnZUNvbXBvbmVudDpjb25kYTMmY2R1dGlsJjguMQ==',
                                'manager': 'conda3',
                                'package': 'cdutil',
                                'version': '8.1'
                            }
                        },
                        {
                            'cursor': 'Mg==',
                            'node': {
                                'fromBase': False,
                                'id': 'UGFja2FnZUNvbXBvbmVudDpjb25kYTMmbmx0ayYzLjIuNQ==',
                                'manager': 'conda3',
                                'package': 'nltk',
                                'version': '3.2.5'
                            }
                        },
                        {
                            'cursor': 'Mw==',
                            'node': {
                                'fromBase': False,
                                'id': 'UGFja2FnZUNvbXBvbmVudDpwaXAmZ3RtdW5pdDEmMC4yLjQ=',
                                'manager': 'pip',
                                'package': 'gtmunit1',
                                'version': '0.2.4'
                            }
                        },
                        {
                            'cursor': 'NA==',
                            'node': {
                                'fromBase': False,
                                'id': 'UGFja2FnZUNvbXBvbmVudDpwaXAmbnVtcHkmMS4xMg==',
                                'manager': 'pip',
                                'package': 'numpy',
                                'version': '1.12'
                            }
                        },
                        {
                            'cursor': 'NQ==',
                            'node': {
                                'fromBase': False,
                                'id': 'UGFja2FnZUNvbXBvbmVudDpwaXAmcmVxdWVzdHMmMS4z',
                                'manager': 'pip',
                                'package': 'requests',
                                'version': '1.3'
                            }
                        }
                    ],
                    'pageInfo': {
                        'hasNextPage': False
                    }
                }
            }
        }
    }
}

snapshots['TestEnvironmentServiceQueries.test_get_package_manager 3'] = {
    'data': {
        'labbook': {
            'environment': {
                'packageDependencies': {
                    'edges': [
                        {
                            'cursor': 'MQ==',
                            'node': {
                                'fromBase': False,
                                'id': 'UGFja2FnZUNvbXBvbmVudDpjb25kYTMmY2R1dGlsJjguMQ==',
                                'manager': 'conda3',
                                'package': 'cdutil',
                                'version': '8.1'
                            }
                        },
                        {
                            'cursor': 'Mg==',
                            'node': {
                                'fromBase': False,
                                'id': 'UGFja2FnZUNvbXBvbmVudDpjb25kYTMmbmx0ayYzLjIuNQ==',
                                'manager': 'conda3',
                                'package': 'nltk',
                                'version': '3.2.5'
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
}

snapshots['TestEnvironmentServiceQueries.test_get_package_manager_metadata 1'] = {
    'data': {
        'labbook': {
            'environment': {
                'packageDependencies': {
                    'edges': [
                    ],
                    'pageInfo': {
                        'hasNextPage': False
                    }
                }
            }
        }
    }
}

snapshots['TestEnvironmentServiceQueries.test_get_package_manager_metadata 2'] = {
    'data': {
        'labbook': {
            'environment': {
                'packageDependencies': {
                    'edges': [
                        {
                            'cursor': 'MA==',
                            'node': {
                                'description': 'A set of tools to manipulate climate data',
                                'docsUrl': 'http://anaconda.org/conda-forge/cdutil',
                                'fromBase': False,
                                'id': 'UGFja2FnZUNvbXBvbmVudDpjb25kYTMmY2R1dGlsJjguMQ==',
                                'latestVersion': '8.1',
                                'manager': 'conda3',
                                'package': 'cdutil',
                                'version': '8.1'
                            }
                        },
                        {
                            'cursor': 'MQ==',
                            'node': {
                                'description': 'Python interface to coveralls.io API\\n',
                                'docsUrl': 'http://anaconda.org/conda-forge/python-coveralls',
                                'fromBase': False,
                                'id': 'UGFja2FnZUNvbXBvbmVudDpjb25kYTMmcHl0aG9uLWNvdmVyYWxscyYyLjUuMA==',
                                'latestVersion': '2.9.3',
                                'manager': 'conda3',
                                'package': 'python-coveralls',
                                'version': '2.5.0'
                            }
                        },
                        {
                            'cursor': 'Mg==',
                            'node': {
                                'description': 'Package 1 for Gigantum Client unit testing.',
                                'docsUrl': 'https://github.com/gigantum/gigantum-client',
                                'fromBase': False,
                                'id': 'UGFja2FnZUNvbXBvbmVudDpwaXAmZ3RtdW5pdDEmMC4yLjE=',
                                'latestVersion': '0.12.4',
                                'manager': 'pip',
                                'package': 'gtmunit1',
                                'version': '0.2.1'
                            }
                        },
                        {
                            'cursor': 'Mw==',
                            'node': {
                                'description': 'Package 1 for Gigantum Client unit testing.',
                                'docsUrl': 'https://github.com/gigantum/gigantum-client',
                                'fromBase': False,
                                'id': 'UGFja2FnZUNvbXBvbmVudDpwaXAmZ3RtdW5pdDImMTIuMg==',
                                'latestVersion': '12.2',
                                'manager': 'pip',
                                'package': 'gtmunit2',
                                'version': '12.2'
                            }
                        },
                        {
                            'cursor': 'NA==',
                            'node': {
                                'description': 'Package 1 for Gigantum Client unit testing.',
                                'docsUrl': 'https://github.com/gigantum/gigantum-client',
                                'fromBase': False,
                                'id': 'UGFja2FnZUNvbXBvbmVudDpwaXAmZ3RtdW5pdDMmNS4w',
                                'latestVersion': '5.0',
                                'manager': 'pip',
                                'package': 'gtmunit3',
                                'version': '5.0'
                            }
                        }
                    ],
                    'pageInfo': {
                        'hasNextPage': False
                    }
                }
            }
        }
    }
}

snapshots['TestEnvironmentServiceQueries.test_bundle_app_query 1'] = {
    'data': {
        'labbook': {
            'environment': {
                'bundledApps': [
                ]
            },
            'id': 'TGFiYm9vazpkZWZhdWx0JmxhYmJvb2stYnVuZGxl'
        }
    }
}

snapshots['TestEnvironmentServiceQueries.test_bundle_app_query 2'] = {
    'data': {
        'labbook': {
            'environment': {
                'bundledApps': [
                    {
                        'appName': 'dash 1',
                        'command': 'python app1.py',
                        'description': 'a demo dash app 1',
                        'id': 'QnVuZGxlZEFwcDpkZWZhdWx0JmxhYmJvb2stYnVuZGxlJmRhc2ggMQ==',
                        'port': 8050
                    },
                    {
                        'appName': 'dash 2',
                        'command': 'python app2.py',
                        'description': 'a demo dash app 2',
                        'id': 'QnVuZGxlZEFwcDpkZWZhdWx0JmxhYmJvb2stYnVuZGxlJmRhc2ggMg==',
                        'port': 9000
                    },
                    {
                        'appName': 'dash 3',
                        'command': 'python app3.py',
                        'description': 'a demo dash app 3',
                        'id': 'QnVuZGxlZEFwcDpkZWZhdWx0JmxhYmJvb2stYnVuZGxlJmRhc2ggMw==',
                        'port': 9001
                    }
                ]
            },
            'id': 'TGFiYm9vazpkZWZhdWx0JmxhYmJvb2stYnVuZGxl'
        }
    }
}

snapshots['TestEnvironmentServiceQueries.test_package_query_with_errors 1'] = {
    'data': {
        'labbook': {
            'checkPackages': [
                {
                    'description': 'Package 1 for Gigantum Client unit testing.',
                    'id': 'UGFja2FnZUNvbXBvbmVudDpwaXAmZ3RtdW5pdDEmMC4yLjQ=',
                    'isValid': True,
                    'latestVersion': '0.12.4',
                    'manager': 'pip',
                    'package': 'gtmunit1',
                    'version': '0.2.4'
                },
                {
                    'description': 'Package 1 for Gigantum Client unit testing.',
                    'id': 'UGFja2FnZUNvbXBvbmVudDpwaXAmZ3RtdW5pdDImMTAwLjAw',
                    'isValid': False,
                    'latestVersion': '12.2',
                    'manager': 'pip',
                    'package': 'gtmunit2',
                    'version': '100.00'
                },
                {
                    'description': 'Package 1 for Gigantum Client unit testing.',
                    'id': 'UGFja2FnZUNvbXBvbmVudDpwaXAmZ3RtdW5pdDMmNS4w',
                    'isValid': True,
                    'latestVersion': '5.0',
                    'manager': 'pip',
                    'package': 'gtmunit3',
                    'version': '5.0'
                },
                {
                    'description': None,
                    'id': 'UGFja2FnZUNvbXBvbmVudDpwaXAmYXNkZmFzZGZhc2RmJg==',
                    'isValid': False,
                    'latestVersion': None,
                    'manager': 'pip',
                    'package': 'asdfasdfasdf',
                    'version': ''
                }
            ],
            'id': 'TGFiYm9vazpkZWZhdWx0JmxhYmJvb2s1'
        }
    }
}

snapshots['TestEnvironmentServiceQueries.test_package_query_with_errors_conda 1'] = {
    'data': {
        'labbook': {
            'checkPackages': [
                {
                    'description': 'A set of tools to manipulate climate data',
                    'id': 'UGFja2FnZUNvbXBvbmVudDpjb25kYTMmY2R1dGlsJjguMQ==',
                    'isValid': True,
                    'latestVersion': '8.1',
                    'manager': 'conda3',
                    'package': 'cdutil',
                    'version': '8.1'
                },
                {
                    'description': 'Natural Language Toolkit',
                    'id': 'UGFja2FnZUNvbXBvbmVudDpjb25kYTMmbmx0ayYxMDAuMDA=',
                    'isValid': False,
                    'latestVersion': '3.4.4',
                    'manager': 'conda3',
                    'package': 'nltk',
                    'version': '100.00'
                },
                {
                    'description': 'Python interface to coveralls.io API\\n',
                    'id': 'UGFja2FnZUNvbXBvbmVudDpjb25kYTMmcHl0aG9uLWNvdmVyYWxscyYyLjkuMw==',
                    'isValid': True,
                    'latestVersion': '2.9.3',
                    'manager': 'conda3',
                    'package': 'python-coveralls',
                    'version': '2.9.3'
                },
                {
                    'description': None,
                    'id': 'UGFja2FnZUNvbXBvbmVudDpjb25kYTMmdGhpc3Nob3VsZHRvdGFsbHlmYWlsJjEuMA==',
                    'isValid': False,
                    'latestVersion': None,
                    'manager': 'conda3',
                    'package': 'thisshouldtotallyfail',
                    'version': '1.0'
                },
                {
                    'description': None,
                    'id': 'UGFja2FnZUNvbXBvbmVudDpjb25kYTMmbm90YXJlYWxwYWNrYWdlJg==',
                    'isValid': False,
                    'latestVersion': None,
                    'manager': 'conda3',
                    'package': 'notarealpackage',
                    'version': ''
                }
            ],
            'id': 'TGFiYm9vazpkZWZhdWx0JmxhYmJvb2s1Y29uZGE='
        }
    }
}

snapshots['TestEnvironmentServiceQueries.test_package_query_with_errors_apt 1'] = {
    'data': {
        'labbook': {
            'checkPackages': [
                {
                    'description': 'command line tool for transferring data with URL syntax',
                    'id': 'UGFja2FnZUNvbXBvbmVudDphcHQmY3VybCY4LjE=',
                    'isValid': False,
                    'latestVersion': '7.58.0-2ubuntu3.1',
                    'manager': 'apt',
                    'package': 'curl',
                    'version': '8.1'
                },
                {
                    'description': None,
                    'id': 'UGFja2FnZUNvbXBvbmVudDphcHQmbm90YXJlYWxwYWNrYWdlJg==',
                    'isValid': False,
                    'latestVersion': None,
                    'manager': 'apt',
                    'package': 'notarealpackage',
                    'version': ''
                }
            ],
            'id': 'TGFiYm9vazpkZWZhdWx0JmxhYmJvb2s1YXB0'
        }
    }
}

snapshots['TestEnvironmentServiceQueries.test_package_query_no_version 1'] = {
    'data': {
        'labbook': {
            'checkPackages': [
                {
                    'description': 'Package 1 for Gigantum Client unit testing.',
                    'id': 'UGFja2FnZUNvbXBvbmVudDpwaXAmZ3RtdW5pdDEmMC4xMi40',
                    'isValid': True,
                    'latestVersion': '0.12.4',
                    'manager': 'pip',
                    'package': 'gtmunit1',
                    'version': '0.12.4'
                },
                {
                    'description': None,
                    'id': 'UGFja2FnZUNvbXBvbmVudDpwaXAmbm90YXJlYWxwYWNrYWdlJklOVkFMSUQ=',
                    'isValid': False,
                    'latestVersion': None,
                    'manager': 'pip',
                    'package': 'notarealpackage',
                    'version': None
                }
            ],
            'id': 'TGFiYm9vazpkZWZhdWx0JmxhYmJvb2s2bm92ZXJzaW9u'
        }
    }
}

snapshots['TestEnvironmentServiceQueries.test_package_query_no_version 2'] = {
    'data': {
        'labbook': {
            'checkPackages': [
                {
                    'description': 'command line tool for transferring data with URL syntax',
                    'id': 'UGFja2FnZUNvbXBvbmVudDphcHQmY3VybCY3LjU4LjAtMnVidW50dTMuMQ==',
                    'isValid': True,
                    'latestVersion': '7.58.0-2ubuntu3.1',
                    'manager': 'apt',
                    'package': 'curl',
                    'version': '7.58.0-2ubuntu3.1'
                },
                {
                    'description': None,
                    'id': 'UGFja2FnZUNvbXBvbmVudDphcHQmbm90YXJlYWxwYWNrYWdlJklOVkFMSUQ=',
                    'isValid': False,
                    'latestVersion': None,
                    'manager': 'apt',
                    'package': 'notarealpackage',
                    'version': None
                }
            ],
            'id': 'TGFiYm9vazpkZWZhdWx0JmxhYmJvb2s2bm92ZXJzaW9u'
        }
    }
}

snapshots['TestEnvironmentServiceQueries.test_package_query_no_version 3'] = {
    'data': {
        'labbook': {
            'checkPackages': [
                {
                    'description': 'Natural Language Toolkit',
                    'id': 'UGFja2FnZUNvbXBvbmVudDpjb25kYTMmbmx0ayYzLjQuNA==',
                    'isValid': True,
                    'latestVersion': '3.4.4',
                    'manager': 'conda3',
                    'package': 'nltk',
                    'version': '3.4.4'
                },
                {
                    'description': None,
                    'id': 'UGFja2FnZUNvbXBvbmVudDpjb25kYTMmbm90YXJlYWxwYWNrYWdlJklOVkFMSUQ=',
                    'isValid': False,
                    'latestVersion': None,
                    'manager': 'conda3',
                    'package': 'notarealpackage',
                    'version': None
                }
            ],
            'id': 'TGFiYm9vazpkZWZhdWx0JmxhYmJvb2s2bm92ZXJzaW9u'
        }
    }
}
