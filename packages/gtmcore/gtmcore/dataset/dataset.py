import os
import re
import yaml
import datetime
import json

from typing import (Optional, Union)

from gtmcore.gitlib import GitAuthor
from gtmcore.dataset.schemas import validate_dataset_schema
from gtmcore.activity import ActivityStore, ActivityRecord, ActivityDetailType, ActivityType,\
    ActivityAction, ActivityDetailRecord
from gtmcore.activity.utils import ImmutableList, DetailRecordList, TextData
from gtmcore.dataset.storage import get_storage_backend
from gtmcore.dataset.storage.backend import ManagedStorageBackend, UnmanagedStorageBackend

from gtmcore.inventory.repository import Repository


class Dataset(Repository):
    """Class representing a single LabBook"""
    _default_activity_type = ActivityType.DATASET
    _default_activity_detail_type = ActivityDetailType.DATASET
    _default_activity_section = "Dataset Root"

    def __init__(self, config_file: Optional[str] = None, namespace: Optional[str] = None,
                 author: Optional[GitAuthor] = None) -> None:
        super().__init__(config_file, author)
        # TODO - Need a more formalizes solution for differentiating Datasets from other repo types
        self.client_config.config['git']['lfs_enabled'] = False
        self.namespace = namespace
        self._backend: Optional[Union[ManagedStorageBackend, UnmanagedStorageBackend]] = None

    def __str__(self):
        if self._root_dir:
            return f'<Dataset at `{self._root_dir}`>'
        else:
            return f'<Dataset UNINITIALIZED>'

    def __eq__(self, other):
        return isinstance(other, Dataset) and other.root_dir == self.root_dir

    @property
    def id(self) -> str:
        if self._data:
            return self._data["id"]
        else:
            raise ValueError("No ID assigned to the Dataset.")

    @property
    def name(self) -> str:
        if self._data:
            return self._data["name"]
        else:
            raise ValueError("No name assigned to the Dataset.")

    @name.setter
    def name(self, value: str) -> None:
        if not value:
            raise ValueError("value cannot be None or empty")

        if not self._data:
            self._data = {'name': value}
        else:
            self._data["name"] = value
        self._validate_gigantum_data()

        # Update data file
        self._save_gigantum_data()

        # Rename directory
        if self._root_dir:
            base_dir, _ = self._root_dir.rsplit(os.path.sep, 1)
            os.rename(self._root_dir, os.path.join(base_dir, value))
        else:
            raise ValueError("Dataset root dir not specified. Failed to configure git.")

        # Update the root directory to the new directory name
        self._set_root_dir(os.path.join(base_dir, value))

    @property
    def creation_date(self) -> Optional[datetime.datetime]:
        """Get creation date from the gigantum.yaml file"""
        if self._data:
            created_at = self._data["created_on"]
            d = datetime.datetime.strptime(created_at, '%Y-%m-%dT%H:%M:%S.%f')
            d = d.replace(tzinfo=datetime.timezone.utc)  # Make tz aware so rendering in API is consistent
            d = d.replace(microsecond=0)  # Make all times consistent
            return d
        else:
            raise ValueError("No creation date set.")

    @property
    def build_details(self) -> str:
        return self._data["build_info"]

    @property
    def description(self) -> str:
        if self._data:
            return self._data["description"]
        else:
            raise ValueError("No description assigned to this Dataset.")

    @description.setter
    def description(self, value) -> None:
        if not self._data:
            self._data = {'description': value}
        else:
            self._data["description"] = value

        self._save_gigantum_data()

    @property
    def storage_type(self) -> str:
        if self._data:
            return self._data["storage_type"]
        else:
            raise ValueError("No storage type assigned to this Dataset.")

    @storage_type.setter
    def storage_type(self, value) -> None:
        if not self._data:
            self._data = {'storage_type': value}
        else:
            self._data["storage_type"] = value

        self._save_gigantum_data()

    def is_managed(self) -> bool:
        """Property to check if the dataset is managed"""
        is_managed = self.backend.metadata.get("is_managed")
        return is_managed if is_managed is not None else False

    @property
    def backend(self) -> Union[ManagedStorageBackend, UnmanagedStorageBackend]:
        """Property to access the storage backend for this dataset"""
        if not self._backend:
            self._backend = get_storage_backend(self.storage_type)
            self._backend.configuration = self.backend_config

        return self._backend

    @property
    def backend_config(self) -> dict:
        """Property to load the storage.json file"""
        config_file = os.path.join(self.root_dir, ".gigantum", "backend.json")
        if os.path.exists(config_file):
            with open(os.path.join(self.root_dir, ".gigantum", "backend.json"), 'rt') as sf:
                data = json.load(sf)
        else:
            data = dict()

        return data

    @backend_config.setter
    def backend_config(self, data: dict) -> None:
        """Save storage config data"""
        if self._backend:
            self._backend.configuration = {**self._backend.configuration, **data}

        # Remove defaults set at runtime that shouldn't be persisted
        if "username" in data:
            del data["username"]
        if "gigantum_bearer_token" in data:
            del data["gigantum_bearer_token"]
        if "gigantum_id_token" in data:
            del data["gigantum_id_token"]

        config_file = os.path.join(self.root_dir, ".gigantum", "backend.json")
        with open(config_file, 'wt') as sf:
            json.dump(data, sf, indent=2)

        self.git.add(config_file)
        cm = self.git.commit("Updating backend config")

        d = json.dumps(data, indent=2)
        markdown_data = f"Updated dataset storage backend configuration:\n\n ```{d}```"
        adr = ActivityDetailRecord(ActivityDetailType.DATASET, show=False, importance=255,
                                   action=ActivityAction.EDIT, data=TextData('markdown', markdown_data))

        ar = ActivityRecord(ActivityType.DATASET,
                            message="Updated Dataset storage backend configuration",
                            show=True,
                            importance=255,
                            linked_commit=cm.hexsha,
                            detail_objects=DetailRecordList([adr]),
                            tags=ImmutableList(['config']))

        ars = ActivityStore(self)
        ars.create_activity_record(ar)

    def _save_gigantum_data(self) -> None:
        """Method to save changes to the LabBook

        Returns:
            None
        """
        if not self.root_dir:
            raise ValueError("No root directory assigned to Dataset. Failed to get root directory.")

        with open(os.path.join(self.root_dir, ".gigantum", "gigantum.yaml"), 'wt') as df:
            df.write(yaml.safe_dump(self._data, default_flow_style=False))
            df.flush()

    def _load_gigantum_data(self) -> None:
        """Method to load the dataset YAML file to a dictionary

        Returns:
            None
        """
        if not self.root_dir:
            raise ValueError("No root directory assigned to Dataset. Failed to get root directory.")

        with open(os.path.join(self.root_dir, ".gigantum", "gigantum.yaml"), 'rt') as df:
            self._data = yaml.safe_load(df)

    def _validate_gigantum_data(self) -> None:
        """Method to validate the Dataset data file contents

        Returns:
            None
        """
        if not re.match("^(?!-)(?!.*--)[a-z0-9-]+(?<!-)$", self.name):
            raise ValueError("Invalid `name`. Only a-z 0-9 and hyphens allowed. No leading or trailing hyphens.")

        if len(self.name) > 100:
            raise ValueError("Invalid `name`. Max length is 100 characters")

        # Validate schema is supported by running version of the software and valid
        if not validate_dataset_schema(self.schema, self.data):
            import json
            errmsg = f"Schema in Dataset {str(self)} does not match indicated version {self.schema}"
            raise ValueError(errmsg)

    def linked_to(self) -> Optional[str]:
        """Method that provides an identifier to a Project if this instance is linked to a Project (embedded as a
        submodule)

        Returns:
            str
        """
        labbook_key = None
        if ".gigantum/datasets/" in self.root_dir:
            _, username, owner, _, labbook_name, _, _, _, _ = self.root_dir.rsplit("/", 8)
            labbook_key = f"{username}|{owner}|{labbook_name}"

        return labbook_key
