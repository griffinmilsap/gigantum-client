import os
import json

from typing import (Dict, Optional, Any, List)
from collections import OrderedDict

from gtmcore.labbook.labbook import LabBook
from gtmcore.activity import ActivityStore, ActivityType, ActivityRecord, ActivityDetailType, ActivityDetailRecord, \
    ActivityAction
from gtmcore.activity.utils import ImmutableList, DetailRecordList, TextData


class BundledAppManager:
    """Class to manage bundled apps within a labbook instance"""
    def __init__(self, labbook: LabBook) -> None:
        # LabBook Environment
        self.labbook = labbook

    @property
    def bundled_app_file(self):
        return os.path.join(self.labbook.root_dir, '.gigantum', 'bundled_apps.json')

    @property
    def reserved_names(self) -> list:
        """A property for all reserved application names. These are names that are currently used in Gigantum bases

        Returns:
            list
        """
        return ['jupyter', 'notebook', 'jupyterlab', 'rstudio']

    @property
    def reserved_ports(self) -> list:
        """A property for all reserved application ports. The following ports are currently reserved:

        8888 - jupyter
        8787 - rstudio
        8686 - reserved for future expansion
        8585 - reserved for future expansion
        8484 - reserved for future expansion
        8383 - reserved for future expansion

        Returns:
            list
        """
        return [8888, 8787, 8686, 8585, 8484, 8383]

    def add_bundled_app(self, port: int, name: str, description: str, command: Optional[str] = None) -> Dict[str, Any]:
        """Add a "bundled app" configuration to this labbook

        Args:
            port(int): port number to expose from the container (will be routed to the browser)
            name(str): name of the bundled app
            description(str): description of the bundled app
            command(str): command to run in the container if needed to start the app

        Returns:
            dict
        """
        # Check if a reserved application name, currently:
        if name.lower() in self.reserved_names:
            raise ValueError(f"{name} is a reserved application name. Try again.")

        if len(name) > 10 or len(name) < 1:
            raise ValueError(f"{name} must be 10 characters or less.")

        if len(description) > 240:
            raise ValueError(f"{description} must be 240 characters or less.")

        if command:
            if len(command) > 1024:
                raise ValueError(f"{command} must be 1024 characters or less.")

        # Check if a reserved port currently
        if port in self.reserved_ports:
            raise ValueError(f"Port {port} is a in reserved port. Try again.")

        data = self.get_bundled_apps()

        # Check for port already in use
        for app in data:
            if data[app].get('port') == port:
                raise ValueError(f"Port {port} is already in use. Try again.")

        data[name] = {'port': port,
                      'description': description,
                      'command': command}

        with open(self.bundled_app_file, 'wt') as baf:
            json.dump(data, baf)

        # Commit the changes
        self.labbook.git.add(self.bundled_app_file)
        commit = self.labbook.git.commit(f"Committing bundled app")

        adr = ActivityDetailRecord(ActivityDetailType.ENVIRONMENT,
                                   show=False,
                                   action=ActivityAction.CREATE,
                                   data=TextData('plain', f"Added bundled application: {json.dumps(data[name])}"))

        ar = ActivityRecord(ActivityType.ENVIRONMENT,
                            message=f"Added bundled app '{name}'",
                            show=True,
                            linked_commit=commit.hexsha,
                            detail_objects=DetailRecordList([adr]),
                            tags=ImmutableList(["environment", "docker", "bundled_app"]))

        ars = ActivityStore(self.labbook)
        ars.create_activity_record(ar)

        return data

    def remove_bundled_app(self, name: str) -> None:
        """Remove a bundled app from this labbook

        Args:
            name(str): name of the bundled app

        Returns:
            None
        """
        data = self.get_bundled_apps()
        if name not in data:
            raise ValueError(f"App {name} does not exist. Cannot remove.")

        del data[name]

        with open(self.bundled_app_file, 'wt') as baf:
            json.dump(data, baf)

        # Commit the changes
        self.labbook.git.add(self.bundled_app_file)
        commit = self.labbook.git.commit(f"Committing bundled app")

        adr = ActivityDetailRecord(ActivityDetailType.ENVIRONMENT,
                                   show=False,
                                   action=ActivityAction.CREATE,
                                   data=TextData('plain', f"Removed bundled application: {name}"))

        ar = ActivityRecord(ActivityType.ENVIRONMENT,
                            message=f"Removed bundled application: {name}",
                            show=True,
                            linked_commit=commit.hexsha,
                            detail_objects=DetailRecordList([adr]),
                            tags=ImmutableList(["environment", "docker", "bundled_app"]))

        ars = ActivityStore(self.labbook)
        ars.create_activity_record(ar)

    def get_bundled_apps(self) -> OrderedDict:
        """Get collection of bundled apps in this labbook

        Returns:
            None
        """
        if os.path.isfile(self.bundled_app_file):
            with open(self.bundled_app_file, 'rt') as baf:
                data = json.load(baf, object_pairs_hook=OrderedDict)
        else:
            data = OrderedDict()

        return data

    def get_docker_lines(self) -> List[str]:
        """Method to get lines to add to the dockerfile

        Returns:
            list
        """
        lines = list()
        data = self.get_bundled_apps()

        # Check for port already in use
        for app in data:
            lines.append(f"EXPOSE {data[app].get('port')}")

        return lines
