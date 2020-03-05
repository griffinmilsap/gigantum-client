import os
import re
import yaml
import datetime
import glob

from typing import Optional

from gtmcore.exceptions import GigantumException
from gtmcore.gitlib import GitAuthor
from gtmcore.logging import LMLogger
from gtmcore.labbook.schemas import validate_labbook_schema, translate_schema, CURRENT_SCHEMA
from gtmcore.activity import ActivityType, ActivityDetailType

from gtmcore.inventory.repository import Repository

logger = LMLogger.get_logger()


class LabBook(Repository):
    """Class representing a single LabBook"""
    _default_activity_type = ActivityType.LABBOOK
    _default_activity_detail_type = ActivityDetailType.LABBOOK
    _default_activity_section = "Project Root"

    def __init__(self, config_file: Optional[str] = None, author: Optional[GitAuthor] = None) -> None:
        super().__init__(config_file, author)

        # LabBook Environment
        self._env = None

    def __str__(self):
        if self._root_dir:
            return f'<LabBook at `{self._root_dir}`>'
        else:
            return f'<LabBook UNINITIALIZED>'

    def __eq__(self, other):
        return isinstance(other, LabBook) and other.root_dir == self.root_dir

    @property
    def id(self) -> str:
            return self._data["id"]

    @property
    def name(self) -> str:
            return self._data["name"]

    @name.setter
    def name(self, value: str) -> None:
        raise ValueError("Cannot set name")

    @property
    def owner(self) -> Optional[str]:
        try:
            _, owner, _, project_name = self.root_dir.rsplit('/', 3)
            return owner
        except Exception as e:
            return None

    @property
    def creation_date(self) -> datetime.datetime:
        """ Return the timestamp of creation of this project """
        date_str = self._data.get('creation_utc') or self._data['created_on']
        try:
            d = datetime.datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S.%f')
        except ValueError:
            d = datetime.datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S%z')

        # Make tz aware so rendering in API is consistent
        d = d.replace(tzinfo=datetime.timezone.utc)
        # Make all times consistent
        d = d.replace(microsecond=0)
        return d

    @property
    def build_details(self) -> str:
        """ Return details of the Gigantum client application that build this """
        return self._data['build_info']

    @property
    def description(self) -> str:
        return self._data["description"]

    @description.setter
    def description(self, value) -> None:
        self._data["description"] = value
        self._save_gigantum_data()

    @property
    def cuda_version(self) -> Optional[str]:
        """Get the cuda version of the LabBook from the base configuration. If no cuda_version is present, return None

        Returns:

        """
        base_yaml_file = glob.glob(os.path.join(self.root_dir, '.gigantum', 'env', 'base', '*.yaml'))

        if len(base_yaml_file) > 1:
            raise ValueError(f"Project misconfigured. Found {len(base_yaml_file)} base configurations.")
        elif len(base_yaml_file) == 0:
            return None

        # If you got 1 base, load from disk
        with open(base_yaml_file[0], 'rt') as bf:
            base_data = yaml.safe_load(bf)

        return base_data.get('cuda_version')

    @property
    def metadata_path(self) -> str:
        return os.path.join(self.root_dir, '.gigantum')

    @property
    def config_path(self) -> str:
        if self._data['schema'] == 2:
            return os.path.join(self.root_dir, '.gigantum', 'project.yaml')
        else:
            # Backward compatibility loading old projects
            return os.path.join(self.root_dir, '.gigantum', 'labbook.yaml')

    def _save_gigantum_data(self) -> None:
        """Method to save changes to the LabBook

        Returns:
            None
        """
        if not self.root_dir:
            raise ValueError("No root directory assigned to lab book. Failed to get root directory.")

        if self.schema != CURRENT_SCHEMA:
            raise ValueError('Cannot save data to Project with old schema')

        with open(self.config_path, 'wt') as lbfile:
            lbfile.write(yaml.safe_dump(self._data, default_flow_style=False))
            lbfile.flush()

    def _load_gigantum_data(self) -> None:
        """Method to load the labbook YAML file to a dictionary

        Returns:
            None
        """
        if not self.root_dir:
            raise GigantumException("No root directory assigned to lab book. "
                                    "Failed to get root directory.")

        schema_path = os.path.join(self.root_dir, '.gigantum', 'project.yaml')
        old_schema_path = os.path.join(self.root_dir, ".gigantum", "labbook.yaml")

        if os.path.exists(schema_path):
            with open(schema_path, 'rt') as lbfile:
                d = yaml.safe_load(lbfile)
            self._data = d
        elif os.path.exists(old_schema_path):
            # For backward compatibility
            with open(old_schema_path, 'rt') as lbfile:
                d = yaml.safe_load(lbfile)
            # "Virtualize" old schemas into new schemas to support back-compatability
            self._data = translate_schema(d, self.root_dir)
        else:
            if 'gm.workspace' in self.get_branches()['local']:
                logger.warning("Master branch empty, attempting to load gm.workspace")
                self.checkout_branch('gm.workspace')
                self._load_gigantum_data()
            else:
                raise GigantumException('Cannot find configuration yaml file')

    def _validate_gigantum_data(self) -> None:
        """Method to validate the LabBook data file contents

        Returns:
            None
        """
        if not re.match("^(?!-)(?!.*--)[a-z0-9-]+(?<!-)$", self.name):
            raise ValueError("Invalid `name`. Only a-z 0-9 and hyphens allowed. No leading or trailing hyphens.")

        if len(self.name) > 100:
            raise ValueError("Invalid `name`. Max length is 100 characters")

        # Validate schema is supported by running version of the software and valid
        if not validate_labbook_schema(self.schema, self.data):
            errmsg = f"Schema in Labbook {str(self)} does not match indicated version {self.schema}"
            logger.error(errmsg)
            raise ValueError(errmsg)
