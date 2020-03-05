import abc
from gtmcore.logging import LMLogger
from typing import (Any, Dict, List, Optional)
import redis

from gtmcore.activity import ActivityRecord, ActivityStore, ActivityType
from gtmcore.activity.processors.processor import ActivityProcessor, ExecutionData
from gtmcore.container import container_for_context
from gtmcore.inventory.inventory  import InventoryManager
from gtmcore.gitlib.git import GitAuthor

logger = LMLogger.get_logger()


class ActivityMonitor(metaclass=abc.ABCMeta):
    """Class to monitor a kernel/IDE for activity to be processed."""

    def __init__(self, user: str, owner: str, labbook_name: str, monitor_key: str, config_file: str = None,
                 author_name: Optional[str] = None, author_email: Optional[str] = None) -> None:
        """Constructor requires info to load the lab book

        Args:
            user(str): current logged in user
            owner(str): owner of the lab book
            labbook_name(str): name of the lab book
            monitor_key(str): Unique key for the activity monitor in redis
            author_name(str): Name of the user starting this activity monitor
            author_email(str): Email of the user starting this activity monitor
        """
        self.monitor_key = monitor_key

        # List of processor classes that will be invoked in order
        self.processors: List[ActivityProcessor] = []

        # Populate GitAuthor instance if available
        if author_name:
            author: Optional[GitAuthor] = GitAuthor(name=author_name, email=author_email)
        else:
            author = None

        # Load Lab Book instance
        im = InventoryManager(config_file)
        self.labbook = im.load_labbook(user, owner, labbook_name, author=author)
        self.user = user
        self.owner = owner
        self.labbook_name = labbook_name

        # Create ActivityStore instance
        self.activity_store = ActivityStore(self.labbook)

        # A flag indicating if the activity record is OK to store
        self.can_store_activity_record = False

    def add_processor(self, processor_instance: ActivityProcessor) -> None:
        """

        Args:
            processor_instance(ActivityProcessor): A processor class to add to the pipeline

        Returns:
            None
        """
        self.processors.append(processor_instance)

    def commit_file(self, filename: str) -> str:
        """Method to commit changes to a file

        Args:
            filename(str): file to commit

        Returns:
            str
        """
        self.labbook.git.add(filename)
        commit = self.labbook.git.commit("Auto-commit from activity monitoring")
        return commit.hexsha

    def commit_labbook(self) -> str:
        """Method to commit changes to the entire labbook

        Returns:
            str
        """
        self.labbook.git.add_all()
        commit = self.labbook.git.commit("Auto-commit from activity monitoring")
        return commit.hexsha

    def store_activity_record(self, linked_commit: str, activity_record: ActivityRecord) -> ActivityRecord:
        """Method to commit changes to a file

        Args:
            linked_commit(str): Git commit this ActivityRecord is related to
            activity_record(ActivityNote): The populated ActivityNote object returned by the processing pipeline

        Returns:
            str
        """
        activity_record = activity_record.update(linked_commit = linked_commit)

        # Create a activity record
        record = self.activity_store.create_activity_record(activity_record)

        return record

    def process(self, activity_type: ActivityType, data: List[ExecutionData],
                metadata: Dict[str, Any]) -> ActivityRecord:
        """Method to update the result ActivityRecord object based on code and result data

        Args:
            activity_type(ActivityType): A ActivityType object indicating the activity type
            data(list): A list of ExecutionData instances containing the data for this record
            metadata(str): A dictionary containing Dev Env specific or other developer defined data

        Returns:
            ActivityRecord
        """
        # Initialize empty record
        activity_record = ActivityRecord(activity_type=activity_type)

        # Get git status for tracking file changes
        status = self.labbook.git.status()

        # Run processors to populate the record
        for p in self.processors:
            try:
                activity_record = p.process(activity_record, data, status, metadata)
            except:
                msg = f"{type(self).__qualname__} had a problem executing processor {type(p).__qualname__}, the processor will be skipped for this record"
                logger.warning(msg, exc_info=True)

        return activity_record

    def get_container_ip(self) -> Optional[str]:
        """Method to get the monitored lab book container's IP address on the Docker bridge network

        Returns:
            str
        """
        project_container = container_for_context(self.user, labbook=self.labbook)
        ip = project_container.query_container_ip()
        logger.info("container {} IP: {}".format(self.labbook, ip))
        return ip

    def set_busy_state(self, is_busy: bool) -> None:
        """Method to set the busy state of the dev env being monitored. If busy, some actions (e.g. auto-save hooks)
        may be disabled depending on the dev env. This method sets or deletes a key in redis that other processes can
        check

        Args:
            is_busy(bool): True if busy, false if idle

        Returns:

        """
        try:
            client = redis.StrictRedis(db=1)
            key = f"{self.labbook.key}&is-busy&{self.monitor_key}"
            if is_busy:
                client.set(key, "True")
            else:
                client.delete(key)
        except Exception as err:
            # This should never stop more important operations
            logger.warning(f"An error occurred while setting the monitor busy state for {str(self.labbook )}: {err}")

    def start(self, data: Dict[str, Any]) -> None:
        """Method called in a long running scheduled async worker that should monitor for activity, committing files
        and creating notes as needed.

        Args:
            data(dict): A dictionary of data to start the activity monitor

        Returns:
            None
        """
        raise NotImplemented
