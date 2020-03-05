import abc
from typing import (Any, Dict, List)

from gtmcore.activity import ActivityRecord


class ExecutionData(object):
    """A simple class to hold information from the execution of a segment of code for later processing"""
    def __init__(self):
        # list of dictionaries containing code snippets
        self.code: List[Dict[str, Any]] = list()

        # List of dictionaries containing result data
        self.result: List[Dict[str, Any]] = list()

        # List of tags to be stored with the record
        self.tags: List[str] = list()

        # Flag indicating if the block errored and should be ignored
        self.cell_error = False

    def is_empty(self):
        """Helper method to check if any data has been added to the object"""
        if len(self.code) == 0 and len(self.result) == 0 and len(self.tags) == 0:
            return True
        else:
            return False


class ActivityProcessor(metaclass=abc.ABCMeta):
    """Class to process activity and return content for an ActivityRecord"""

    def process(self, result_obj: ActivityRecord, data: List[ExecutionData], status: Dict[str, Any],
                metadata: Dict[str, Any]) -> ActivityRecord:
        """Method to update a result object based on code and result data

        Args:
            result_obj(ActivityNote): An object containing the ActivityRecord
            data(list): A list of ExecutionData instances containing the data for this record
            status(dict): A dictionary containing the git status for this record
            metadata(dict): A dictionary containing Dev Env specific or other developer defined data

        Returns:
            ActivityRecord
        """
        raise NotImplementedError
