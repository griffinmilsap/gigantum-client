import os
import yaml

from typing import (Any, Dict, Optional, Tuple, Mapping, MutableMapping)
from pkg_resources import resource_filename

from gtmcore.logging import LMLogger

logger = LMLogger.get_logger()


def deepupdate(destination: MutableMapping[str, Any], source: Mapping[str, Any]) -> None:
    """An updated version of dict.update that will recursively merge sub-dictionaries
    instead of replacing sub-dictionaries.

    Args:
        destination (MutableMapping[str, object]): Dictionary to update
        source (Mapping[str, object]): Dictionary to update from
    """
    for k, v in source.items():
        if type(v) == dict:
            if k in destination:
                deepupdate(destination[k], v)
            else:
                destination[k] = v
        else:
            destination[k] = v


class Configuration(object):
    """Class to interact with LabManager configuration files    
    """
    INSTALLED_LOCATION = "/etc/gigantum/labmanager.yaml"
    USER_LOCATION = "/mnt/gigantum/.labmanager/config.yaml"

    def __init__(self, config_file: Optional[str] = None) -> None:
        """
        
        Args:
            config_file(str): Absolute path to the configuration file to load
        """
        if config_file:
            self.config_file = config_file
        else:
            self.config_file = self.find_default_config()

        self.config = self.load(self.config_file)

        # If a user config exists, take fields from that to override the default config.
        if os.path.exists(self.USER_LOCATION):
            deepupdate(self.config, self.user_config)

    @staticmethod
    def find_default_config() -> str:
        """Method to find the default configuration file
        
        Returns:
            (str): Absolute path to the file to load
        """
        # Check if file exists in the installed location
        if os.path.isfile(Configuration.INSTALLED_LOCATION):
            return Configuration.INSTALLED_LOCATION
        else:
            # Load default file out of python package
            return os.path.join(resource_filename("gtmcore", "configuration/config"), "labmanager.yaml.default")

    @property
    def app_workdir(self) -> str:
        """Return the Gigantum Client working directory INSIDE the container.

        Note: In a normally built container for actual use (not just testing), this would be `/mnt/gigantum`
        """
        return os.path.expanduser(self.config['git']['working_directory'])

    @property
    def upload_dir(self) -> str:
        """Return the location to write temporary data for uploads. It should be within the workdir so copies
        across filesystems can be avoided.

        """
        return os.path.join(self.app_workdir, '.labmanager', 'upload')

    @property
    def download_cpu_limit(self) -> int:
        """Return the max number of CPUs to use (i.e. concurrent jobs) when downloading dataset files

        Will limit to a maximum of 8 workers if auto returns more than 8. This will avoid most bandwidth issues.
        If a user has a ton of bandwidth, they can adjust this setting manually in the config file to blast.

        Returns:
            int
        """
        config_val = self.config['datasets']['download_cpu_limit']
        if config_val == 'auto':
            num_cpus = os.cpu_count()
            if not num_cpus:
                num_cpus = 1
            if num_cpus > 8:
                num_cpus = 8
            return num_cpus
        else:
            return int(config_val)

    @property
    def is_hub_client(self) -> bool:
        """Return true if configured as a client to run in the hub

        Returns:
            bool
        """
        context = self.config['container']['context']
        if context == "hub":
            return True
        else:
            return False

    @property
    def upload_cpu_limit(self) -> int:
        """Return the max number of CPUs to use (i.e. concurrent jobs) when uploading dataset files

        Will limit to a maximum of 8 workers if auto returns more than 8. This will avoid most bandwidth issues.
        If a user has a ton of bandwidth, they can adjust this setting manually in the config file to blast.

        Returns:
            int
        """
        config_val = self.config['datasets']['upload_cpu_limit']
        if config_val == 'auto':
            num_cpus = os.cpu_count()
            if not num_cpus:
                num_cpus = 1
            if num_cpus > 8:
                num_cpus = 8
            return num_cpus
        else:
            return int(config_val)

    @property
    def user_config(self) -> Dict[str, Any]:
        """Return the configuration items loaded from the user's config.yaml"""

        if self.config_file != self.find_default_config():
            # If we are using a custom config file, then disregard any
            # user overrides (This is used only in testing)
            return {}
        elif os.path.exists(self.USER_LOCATION):
            user_conf_data = self._read_config_file(self.USER_LOCATION)
            return user_conf_data
        else:
            return {}

    def _read_config_file(self, config_file: str) -> Dict[str, Any]:
        """Method to read a config file into a dictionary

        Args:
            config_file(str): Absolute path to a configuration file

        Returns:
            (dict)
        """
        with open(config_file, "rt") as cf:
            # If the config file is empty or only comments, we create an empty dict to allow `deepupdate()` to work
            data = yaml.safe_load(cf) or {}

        # Check if there is a parent config file to inherit from
        if "from" in data.keys():
            if data["from"]:
                if os.path.isfile(data["from"]):
                    # Absolute path provided
                    parent_config_file = data["from"]
                else:
                    # Just a filename provided
                    parent_config_file = os.path.join(os.path.dirname(config_file), data["from"])

                # Load Parent data and add/overwrite keys as needed
                parent_data = self._read_config_file(parent_config_file)
                deepupdate(parent_data, data) # Update parent_data with current values from data
                data = parent_data

        return data

    def load(self, config_file: str = None) -> Dict[str, Any]:
        """Method to load a config file

        Args:
            config_file(str): Absolute path to a configuration file

        Returns:
            (dict)
        """
        if not config_file:
            config_file = self.config_file

        data = self._read_config_file(config_file)
        return data

    def save(self, config_file: str = None) -> None:
        """Method to save a configuration to file
        
        Args:
            config_file(str): Absolute path to a configuration file

        Returns:
            None
        """
        if not config_file:
            config_file = self.config_file

        logger.info("Writing config file to {}".format(self.config_file))
        with open(config_file, "wt") as cf:
            cf.write(yaml.safe_dump(self.config, default_flow_style=False))

    def get_remote_configuration(self, remote_name: Optional[str] = None) -> Dict[str, str]:
        """Method to load the configuration for a remote server

        Args:
            remote_name: Name of the remote to lookup, if omitted uses the default remote

        Returns:

        """
        if not remote_name:
            remote_name = self.config['git']['default_remote']

        try:
            result = self.config['git']['remotes'][remote_name].copy()
            result['git_remote'] = remote_name
            return result

        except KeyError:
            raise ValueError(f'Configuration for {remote_name} could not be found')

    def get_hub_api_url(self, remote_name: Optional[str] = None) -> str:
        """Method to return the url for the desired Gigantum Hub API

        Args:
            remote_name: Name of the remote to lookup, if omitted uses the default remote

        Returns:

        """
        remote_config = self.get_remote_configuration(remote_name)

        return remote_config['hub_api']
