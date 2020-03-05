import json
from contextlib import contextmanager
from enum import Enum
from typing import (Any, List, Tuple, Optional, Dict, overload)
import base64
import blosc
import copy
import operator
import datetime
from dataclasses import field, dataclass

from gtmcore.activity.utils import ImmutableDict, ImmutableList, SortedImmutableList, DetailRecordList
from gtmcore.activity.serializers import Serializer
from gtmcore.exceptions import GigantumException
from gtmcore.logging import LMLogger

logger = LMLogger.get_logger()

class ActivityType(Enum):
    """Enumeration representing the type of Activity Record"""
    # User generated Notes
    NOTE = 0
    # For any changes to the environment config
    ENVIRONMENT = 1
    # Anything related to files in the code directory or execution
    CODE = 2
    # Anything related to files in the input directory
    INPUT_DATA = 3
    # Anything related to files in the output directory
    OUTPUT_DATA = 4
    # A milestone record
    MILESTONE = 5
    # A branch record
    BRANCH = 6
    # A record for any high-level labbook ops
    LABBOOK = 7
    # A record for any high-level dataset ops
    DATASET = 8


class ActivityDetailType(Enum):
    """Enumeration representing the type of Activity Detail Record"""
    # Any dataset level changes (e.g. create, rename)
    DATASET = 8
    # User generated Notes
    NOTE = 7
    # Any labbook level changes (e.g. create, rename)
    LABBOOK = 6
    # Anything related to files in the input directory
    INPUT_DATA = 5
    # Anything related to files in the code directory
    CODE = 4
    # For storing the executed block of code
    CODE_EXECUTED = 3
    # For storing results from running code
    RESULT = 2
    # Anything related to files in the input directory
    OUTPUT_DATA = 1
    # For any changes to the environment config
    ENVIRONMENT = 0


class ActivityAction(Enum):
    """Enumeration representing the modifiers on Activity Detail Records"""
    NOACTION = 0
    CREATE = 1
    EDIT = 2
    DELETE = 3
    EXECUTE = 4


class ActivityDetailRecordEncoder(json.JSONEncoder):
    """Custom JSON encoder to encoded binary data as base64 when serializing to json"""
    def default(self, obj):
        if isinstance(obj, bytes):
            return base64.b64encode(obj).decode("UTF-8")

        return json.JSONEncoder.default(self, obj)


@dataclass(frozen = True)
class ActivityDetailRecord(object):
    """A class to represent an activity detail entry that can be stored in an activity entry

    Attributes:
        detail_type: Type indicating the category of detail
        key: Key used to load detail record from the embedded detail DB
        data:  Storage for detail record data, organized by MIME type to support proper rendering
        action: Action for this detail record
        show: Boolean indicating if this item should be "shown" or "hidden"
        importance: A score indicating the importance, currently expected to range from 0-255
        tags: A list of tags for the record
    """

    # Type indicating the category of detail
    detail_type: ActivityDetailType

    @property
    def type(self):
        """Alias for detail_type for backwards compatibility"""
        return self.detail_type

    # Key used to load detail record from the embedded detail DB
    key: Optional[str] = None

    # Storage for detail record data, organized by MIME type to support proper rendering
    data: ImmutableDict[str, str] = field(default_factory = ImmutableDict)

    # Action for this detail record
    action: ActivityAction = ActivityAction.NOACTION

    # Boolean indicating if this item should be "shown" or "hidden"
    show: bool = True

    # A score indicating the importance, currently expected to range from 0-255
    importance: int = 0

    # A list of tags for the record
    tags: ImmutableList[str] = field(default_factory = ImmutableList)

    def update(self, 
               detail_type: Optional[ActivityDetailType] = None,
               key: Optional[str] = None,
               data: Optional[ImmutableDict[str, str]] = None,
               action: Optional[ActivityAction] = None,
               show: Optional[bool] = None,
               importance: Optional[int] = None,
               tags: Optional[ImmutableList[str]] = None) -> 'ActivityDetailRecord':
        l = locals()
        def find(name):
            v = l[name]
            if v is None:
                v = getattr(self,name)
            return v

        return ActivityDetailRecord(detail_type = find('detail_type'),
                                    key = find('key'),
                                    data = find('data'),
                                    action = find('action'),
                                    show = find('show'),
                                    importance = find('importance'),
                                    tags = find('tags'))

    @property
    def is_loaded(self):
        """Flag indicating if this record object has been populated with data
           (used primarily during lazy loading)
        """
        # If data has been added, it can be accessed now
        return len(self.data) > 0

    @property
    def log_str(self) -> str:
        """Method to create the identifying string stored in the git log

        Returns:
            str
        """
        if not self.key:
            raise ValueError("Detail Object key must be set before accessing the log str.")

        return "{},{},{},{},{}".format(self.type.value, int(self.show), self.importance, self.key, self.action.value)

    @staticmethod
    def from_log_str(log_str: str) -> 'ActivityDetailRecord':
        """Static method to create a ActivityDetailRecord instance from the identifying string stored in the git log

        Args:
            log_str(str): the identifying string stored in the git lo

        Returns:
            ActivityDetailRecord
        """
        try:
            type_int, show_int, importance, key, action_int = log_str.split(',')
        except ValueError:
            # Legacy record with no Action modifier available
            type_int, show_int, importance, key = log_str.split(',')
            action_int = "0"  # No action

        return ActivityDetailRecord(ActivityDetailType(int(type_int)), show=bool(int(show_int)),
                                    importance=int(importance), key=key, action=ActivityAction(int(action_int)))

    def add_value(self, mime_type: str, value: str) -> 'ActivityDetailRecord':
        """Method to add data to this record by MIME type

        Args:
            mime_type(str): The MIME type of the representation of the object
            value(Any): The value for this record

        Returns:
            ActivityDetailRecord
        """
        if mime_type in self.data:
            raise ValueError("Attempting to duplicate a MIME type while adding detail data")

        # Store value
        return self.update(data = self.data.set(mime_type, value))

    @property
    def data_size(self) -> int:
        """A property to get the uncompressed byte count for detail objects

        Returns:
            int
        """
        obj_size = 0
        for mime_type in self.data:
            obj_size += len(self.data[mime_type])

        return obj_size

    def to_dict(self, compact=False) -> dict:
        """Method to convert to a dictionary

        Args:
            compact(bool): Flag indicating if compact values should be used (default when storing to log)

        Returns:
            dict
        """
        if compact:
            # Compact representation and do deep copy so binary conversions don't stick around in the object
            return {"t": self.type.value,
                    "i": self.importance,
                    "s": int(self.show),
                    "d": copy.deepcopy(dict(self.data)),
                    "a": list(self.tags),
                    "n": self.action.value
                    }
        else:
            return {"type": self.type.value,
                    "importance": self.importance,
                    "show": self.show,
                    "data": dict(self.data),
                    "tags": list(self.tags),
                    "action": self.action.value
                    }

    def to_bytes(self, compress: bool=True) -> bytes:
        """Method to serialize to bytes for storage in the activity detail db

        Returns:
            bytes
        """
        dict_data = self.to_dict(compact=True)

        # Serialize data items
        serializer_obj = Serializer()
        for mime_type in dict_data['d']:
            dict_data['d'][mime_type] = serializer_obj.serialize(mime_type, dict_data['d'][mime_type])

            # Compress object data
            if compress:
                if type(dict_data['d'][mime_type]) != bytes:
                    raise ValueError("Data must be serialized to bytes before compression")

                dict_data['d'][mime_type] = blosc.compress(dict_data['d'][mime_type], typesize=8,
                                                           cname='blosclz',
                                                           shuffle=blosc.SHUFFLE)

        # Base64 encode binary data while dumping to json string
        return json.dumps(dict_data, cls=ActivityDetailRecordEncoder, separators=(',', ':')).encode('utf-8')

    @staticmethod
    def from_bytes(byte_array: bytes, decompress: bool=True, key: Optional[str] = None) -> 'ActivityDetailRecord':
        """Method to create ActivityDetailRecord from byte array (typically stored in the detail db)

        Returns:
            ActivityDetailRecord
        """
        serializer_obj = Serializer()

        obj_dict = json.loads(byte_array.decode('utf-8'))

        # Base64 decode detail data
        for mime_type in obj_dict['d']:
            obj_dict['d'][mime_type] = base64.b64decode(obj_dict['d'][mime_type])

            # Optionally decompress
            if decompress:
                obj_dict['d'][mime_type] = blosc.decompress(obj_dict['d'][mime_type])

            # Deserialize
            obj_dict['d'][mime_type] = serializer_obj.deserialize(mime_type, obj_dict['d'][mime_type])

        # Return new instance
        new_instance = ActivityDetailRecord(detail_type=ActivityDetailType(obj_dict['t']),
                                            key=key,
                                            show=bool(obj_dict["s"]),
                                            importance=obj_dict["i"],
                                            # add tags if present (missing in "old" labbooks)
                                            tags=ImmutableList(obj_dict['a'] if 'a' in obj_dict else []),
                                            # add action if present (missing in "old" labbooks)
                                            action=ActivityAction(int(obj_dict['n']))
                                                   if 'n' in obj_dict else ActivityAction.NOACTION,
                                            data=obj_dict['d'])

        return new_instance

    def to_json(self) -> str:
        """Method to convert to a single dictionary of data, that will serialize to JSON

        Returns:
            dict
        """
        # Get base dict
        dict_data = self.to_dict()

        # jsonify the data
        serializer_obj = Serializer()
        for mime_type in dict_data['data']:
            dict_data['data'][mime_type] = serializer_obj.jsonify(mime_type, dict_data['data'][mime_type])

        # At this point everything in dict_data should be ready to go for JSON serialization
        return json.dumps(dict_data, cls=ActivityDetailRecordEncoder, separators=(',', ':'))

    def jsonify_data(self) -> Dict[str, Any]:
        """Method to convert just the data to JSON safe dictionary

        Returns:
            dict
        """
        dict_data: dict = dict()

        # jsonify the data
        serializer_obj = Serializer()
        for mime_type in self.data:
            dict_data[mime_type] = serializer_obj.jsonify(mime_type, self.data[mime_type])

        # At this point everything in dict_data should be ready to go for JSON serialization
        return dict_data


@dataclass(frozen=True)
class ActivityRecord(object):
    """Class representing an ActivityRecord

    Attributes:
        activity_type: Type indicating the category of detail
        commit: Commit hash of this record in the git log
        linked_commit: Commit hash of the commit this references
        message: Message summarizing the event
        detail_objects: Storage for detail objects
        show: Boolean indicating if this item should be "shown" or "hidden"
        importance: A score indicating the importance, currently expected to range from 0-255
        timestamp: The datetime that the record was written to the git log
        tags: A list of tags for the entire record
        username: Username of the user who created the activity record
        email: Email of the user who created the activity record
    """

    # Type indicating the category of detail
    activity_type: ActivityType

    @property
    def type(self):
        """Alias for activity_type for backwards compatibility"""
        return self.activity_type

    # Commit hash of this record in the git log
    commit: Optional[str] = None

    # Commit hash of the commit this references
    linked_commit: Optional[str] = None

    # Message summarizing the event
    message: Optional[str] = None

    # Storage for detail objects in a tuple of (show, type (enum *value*), importance, object)
    detail_objects: SortedImmutableList[ActivityDetailRecord] = field(default_factory=DetailRecordList)

    # Boolean indicating if this item should be "shown" or "hidden"
    show: bool = True

    # A score indicating the importance, currently expected to range from 0-255
    importance: Optional[int] = None

    # The datetime that the record was written to the git log
    timestamp: Optional[datetime.datetime] = None

    # A list of tags for the entire record
    tags: ImmutableList[str] = field(default_factory=ImmutableList)

    # Username of the user who created the activity record
    username: Optional[str] = None

    # Email of the user who created the activity record
    email: Optional[str] = None

    def update(self,
               activity_type: Optional[ActivityType] = None,
               commit: Optional[str] = None,
               linked_commit: Optional[str] = None,
               message: Optional[str] = None,
               detail_objects: Optional[SortedImmutableList[ActivityDetailRecord]] = None,
               show: Optional[bool] = None,
               importance: Optional[int] = None,
               timestamp: Optional[datetime.datetime] = None,
               tags: Optional[ImmutableList[str]] = None,
               username: Optional[str] = None,
               email: Optional[str] = None) -> 'ActivityRecord':
        l = locals()

        def find(name):
            v = l[name]
            if v is None:
                v = getattr(self, name)
            return v

        return ActivityRecord(activity_type = find('activity_type'),
                              commit = find('commit'),
                              linked_commit = find('linked_commit'),
                              message = find('message'),
                              detail_objects = find('detail_objects'),
                              show = find('show'),
                              importance = find('importance'),
                              timestamp = find('timestamp'),
                              tags = find('tags'),
                              username = find('username'),
                              email = find('email'))

    @property
    def num_detail_objects(self):
        return len(self.detail_objects)

    def trim_detail_objects(self, num_objects: int) -> 'ActivityRecord':
        if num_objects < 1:
            raise ValueError("Cannot set `num_objects` less than 1")

        return self.update(detail_objects = self.detail_objects[0:num_objects])

    def add_detail_object(self, obj: ActivityDetailRecord) -> 'ActivityRecord':
        """Method to add a detail object"""
        return self.update(detail_objects = self.detail_objects.append(obj))

    def set_visibility(self, tags: Dict[str, str]) -> 'ActivityRecord':
        updated = []
        for detail in self.detail_objects:
            directive = 'auto'

            # We don't filter on .startswith('ex') here, so we can use other tags in future
            # Note also that
            for tag in detail.tags:
                try:
                    # Currently show is the only attribute we update
                    directive = tags[tag]
                    if directive == 'show':
                        detail = detail.update(show = True)
                        break
                    elif directive == 'hide':
                        detail = detail.update(show = False)
                        break
                    elif directive in ['ignore', 'auto']:
                        # 'ignore' is handled below - this will be dropped
                        break

                except KeyError:
                    pass

            if directive != 'ignore':
                updated.append(detail)

        return self.update(detail_objects = DetailRecordList(updated))

    @staticmethod
    def from_log_str(log_str: str, commit: str, timestamp: datetime.datetime,
                     username: Optional[str] = None, email: Optional[str] = None) -> 'ActivityRecord':
        """Static method to create a ActivityRecord instance from the identifying string stored in the git log

        Args:
            log_str(str): the identifying string stored in the git log
            commit(str): Optional commit hash for this activity record
            timestamp(datetime.datetime): datetime the record was written to the git log
            username(str): Username of the user who created the commit
            email(str): email of the user who created the commit

        Returns:
            ActivityRecord
        """
        # Validate it is a record
        if log_str[0:20] == "_GTM_ACTIVITY_START_" and log_str[-18:] == "_GTM_ACTIVITY_END_":
            lines = log_str.split("**\n")
            message = lines[1][4:]
            metadata = json.loads(lines[2][9:])

            # Create record
            activity_record = ActivityRecord(ActivityType(metadata["type"]), message=message,
                                             show=metadata["show"],
                                             importance=metadata["importance"],
                                             timestamp=timestamp,
                                             tags=ImmutableList(metadata["tags"]),
                                             linked_commit=metadata['linked_commit'],
                                             username=username,
                                             email=email)
            if commit:
                activity_record = activity_record.update(commit = commit)

            # Add detail records
            detail_objects = []
            for line in lines[4:]:
                if line == "_GTM_ACTIVITY_END_":
                    break

                # Append records
                detail_objects.append(ActivityDetailRecord.from_log_str(line))

            activity_record = activity_record.update(detail_objects = DetailRecordList(detail_objects))

            return activity_record
        else:
            raise ValueError("Malformed git log record. Cannot parse.")

    @property
    def log_str(self) -> str:
        """A property to create the identifying string stored in the git log

        Returns:
            str
        """
        if self.message:
            log_str = f"_GTM_ACTIVITY_START_**\nmsg:{self.message}**\n"
        else:
            raise ValueError("Message required when creating an activity object")

        meta = {"show": self.show, "importance": self.importance or 0, "type": self.type.value,
                'linked_commit': self.linked_commit, 'tags': list(self.tags if self.tags else list())}
        log_str = f"{log_str}metadata:{json.dumps(meta, separators=(',', ':'))}**\n"
        log_str = f"{log_str}details:**\n"
        if self.detail_objects:
            for d in self.detail_objects:
                log_str = f"{log_str}{d.log_str}**\n"

        log_str = f"{log_str}_GTM_ACTIVITY_END_"

        return log_str
