# -*- coding: utf-8 -*-
# snapshottest: v1 - https://goo.gl/zC4yUc
from __future__ import unicode_literals

from snapshottest import Snapshot


snapshots = Snapshot()

snapshots['TestDatasetFilesMutations.test_move_dataset_file 1'] = {
    'data': {
        'moveDatasetFile': {
            'updatedEdges': [
                {
                    'node': {
                        'id': 'RGF0YXNldEZpbGU6ZGVmYXVsdCZkYXRhc2V0LW1vdmUmdGVzdDEtcmVuYW1lZC50eHQ=',
                        'isDir': False,
                        'isLocal': True,
                        'key': 'test1-renamed.txt',
                        'size': '14'
                    }
                }
            ]
        }
    }
}

snapshots['TestDatasetFilesMutations.test_move_dataset_dir 1'] = {
    'data': {
        'moveDatasetFile': {
            'updatedEdges': [
                {
                    'node': {
                        'id': 'RGF0YXNldEZpbGU6ZGVmYXVsdCZkYXRhc2V0LW1vdmUmb3RoZXJfZGlyL2ZpcnN0X2Rpci8=',
                        'isDir': True,
                        'isLocal': True,
                        'key': 'other_dir/first_dir/',
                        'size': '0'
                    }
                },
                {
                    'node': {
                        'id': 'RGF0YXNldEZpbGU6ZGVmYXVsdCZkYXRhc2V0LW1vdmUmb3RoZXJfZGlyL2ZpcnN0X2Rpci90ZXN0My50eHQ=',
                        'isDir': False,
                        'isLocal': True,
                        'key': 'other_dir/first_dir/test3.txt',
                        'size': '8'
                    }
                }
            ]
        }
    }
}

snapshots['TestDatasetFilesMutations.test_move_dataset_dir 2'] = {
    'data': {
        'moveDatasetFile': {
            'updatedEdges': [
                {
                    'node': {
                        'id': 'RGF0YXNldEZpbGU6ZGVmYXVsdCZkYXRhc2V0LW1vdmUmb3RoZXJfZGlyX3JlbmFtZWQv',
                        'isDir': True,
                        'isLocal': True,
                        'key': 'other_dir_renamed/',
                        'size': '0'
                    }
                },
                {
                    'node': {
                        'id': 'RGF0YXNldEZpbGU6ZGVmYXVsdCZkYXRhc2V0LW1vdmUmb3RoZXJfZGlyX3JlbmFtZWQvZmlyc3RfZGlyLw==',
                        'isDir': True,
                        'isLocal': True,
                        'key': 'other_dir_renamed/first_dir/',
                        'size': '0'
                    }
                },
                {
                    'node': {
                        'id': 'RGF0YXNldEZpbGU6ZGVmYXVsdCZkYXRhc2V0LW1vdmUmb3RoZXJfZGlyX3JlbmFtZWQvbmVzdGVkX2Rpci8=',
                        'isDir': True,
                        'isLocal': True,
                        'key': 'other_dir_renamed/nested_dir/',
                        'size': '0'
                    }
                },
                {
                    'node': {
                        'id': 'RGF0YXNldEZpbGU6ZGVmYXVsdCZkYXRhc2V0LW1vdmUmb3RoZXJfZGlyX3JlbmFtZWQvZmlyc3RfZGlyL3Rlc3QzLnR4dA==',
                        'isDir': False,
                        'isLocal': True,
                        'key': 'other_dir_renamed/first_dir/test3.txt',
                        'size': '8'
                    }
                },
                {
                    'node': {
                        'id': 'RGF0YXNldEZpbGU6ZGVmYXVsdCZkYXRhc2V0LW1vdmUmb3RoZXJfZGlyX3JlbmFtZWQvbmVzdGVkX2Rpci90ZXN0Ni50eHQ=',
                        'isDir': False,
                        'isLocal': True,
                        'key': 'other_dir_renamed/nested_dir/test6.txt',
                        'size': '8'
                    }
                },
                {
                    'node': {
                        'id': 'RGF0YXNldEZpbGU6ZGVmYXVsdCZkYXRhc2V0LW1vdmUmb3RoZXJfZGlyX3JlbmFtZWQvbmVzdGVkX2Rpci90ZXN0Ny50eHQ=',
                        'isDir': False,
                        'isLocal': True,
                        'key': 'other_dir_renamed/nested_dir/test7.txt',
                        'size': '7'
                    }
                }
            ]
        }
    }
}
