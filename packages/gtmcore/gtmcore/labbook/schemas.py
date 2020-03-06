import json
import os
from typing import Any, Dict, Optional
from schema import (Schema, SchemaError, Optional as SchemaOptional,
                    Or as SchemaOr, Use as SchemaUse)

import yaml

from gtmcore.logging import LMLogger

logger = LMLogger.get_logger()

# The current LabBook schema version
CURRENT_SCHEMA = 2

LABBOOK_SCHEMA_VERSIONS = {
    # Note: Each time a new schema version is needed, add it into this dictionary
    # with its version number as its key.
    #
    # These are all the supported schemas
    2: {
        'schema': int,
        'id': str,
        'name': str,
        # Does description belong here? I feel like this should be written once.
        'description': str,

        # Timestamp this Gigantum Project was created
        'created_on': str,

        # Details of the application that created it
        'build_info': str,

        # Boolean to indicate whether this was migrated from schema 1
        SchemaOptional('migrated'): bool
    },

    1: {
        # TODO next time we version schema remove cuda_version.  It is no longer used.  Ask RB
        SchemaOptional('cuda_version'): SchemaOr(SchemaUse(str), None),
        'labbook': {
            'id': str,
            'name': str,
            'description': str
        },
        'owner': {
            'username': str
        },
        'schema': int
    }
}


def migrate_schema_to_current(root_dir: str) -> None:
    """ Takes a root directory and re-writes the file containing
        project data to be compliant with the most up-to-date schema.
    """

    l = os.path.join(root_dir, '.gigantum', 'labbook.yaml')
    with open(l, 'rt') as project_file:
        lb_dict = yaml.safe_load(project_file)
    migrated_schema = translate_schema(lb_dict, root_dir)

    p = os.path.join(root_dir, '.gigantum', 'buildinfo')
    if os.path.exists(p):
        logger.warning(f"Removing buildinfo for project at {root_dir}")
        os.remove(p)

    migrated_schema['schema'] = CURRENT_SCHEMA
    migrated_schema['migrated'] = True
    info_path = os.path.join(root_dir, '.gigantum', 'project.yaml')
    with open(info_path, 'w') as info_file:
        logger.warning(f'Migrating schema to {CURRENT_SCHEMA} in {info_path}')
        info_file.write(yaml.safe_dump(migrated_schema, default_flow_style=False))

    # Remove old labbook.yaml
    if os.path.exists(l):
        os.remove(l)

def translate_schema(lb_dict: Dict, root_dir: str) -> Dict:
    if 'schema' not in lb_dict:
        raise ValueError('Unknown schema')

    schema_version = lb_dict['schema']
    if schema_version == CURRENT_SCHEMA:
        return lb_dict

    p = os.path.join(root_dir, '.gigantum', 'buildinfo')
    created_on = None
    build_info = None
    if os.path.exists(p):
        d = json.load(open(p))
        created_on = d['creation_utc']
        build_info = ' :: '.join(
            (d['build_info']['application'],
             d['build_info']['built_on'],
             d['build_info']['revision'][:8]))
    else:
        created_on = '1970-01-01T00:00:00.000'
        build_info = 'Gigantum Client Alpha Build (Unknown Date)'

    return {
        'schema': schema_version,
        'id': lb_dict['labbook']['id'],
        'name': lb_dict['labbook']['name'],
        'description': lb_dict['labbook']['description'],
        'created_on': created_on,
        'build_info': build_info
    }


def validate_labbook_schema(schema_version: int, lb_data: Optional[Dict[str, Any]]) -> bool:
    """ Validate a labbook's data against a known schema. Returns true if schema matches
    version appropriately.

    Args:
        schema_version(int): Schema version to validate against
        lb_data(Dict): Labbook's data dict.

    Returns:
        bool: True if schema validates, False otherwise.

    """
    if not schema_version or schema_version not in LABBOOK_SCHEMA_VERSIONS.keys():
        logger.error(f"schema_version {schema_version} not found in schema versions")
        return False

    if not lb_data:
        logger.error(f"lb_data is None or empty")
        return False

    lb_data_translate = lb_data #translate_schema(lb_data, '')
    schema = Schema(LABBOOK_SCHEMA_VERSIONS[CURRENT_SCHEMA])
    try:
        schema.validate(lb_data_translate)
        return True
    except SchemaError as e:
        logger.error(e)
        return False
