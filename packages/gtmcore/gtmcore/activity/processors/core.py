from typing import (Any, Dict, List)

from gtmcore.activity.processors.processor import ActivityProcessor, ExecutionData
from gtmcore.activity import ActivityRecord, ActivityDetailRecord, ActivityAction, ActivityDetailType
from gtmcore.activity.utils import TextData, DetailRecordList
from gtmcore.labbook import LabBook

from gtmcore.logging import LMLogger
logger = LMLogger.get_logger()

class ActivityShowBasicProcessor(ActivityProcessor):
    """Class to simply hide an activity record if it doesn't have any detail records that are set to show=True"""

    def process(self, result_obj: ActivityRecord, data: List[ExecutionData],
                status: Dict[str, Any], metadata: Dict[str, Any]) -> ActivityRecord:
        """Method to update a result object based on code and result data

        Args:
            result_obj(ActivityNote): An object containing the note
            data(list): A list of ExecutionData instances containing the data for this record
            status(dict): A dict containing the result of git status from gitlib
            metadata(str): A dictionary containing Dev Env specific or other developer defined data

        Returns:
            ActivityNote
        """
        show = False
        for detail in result_obj.detail_objects:
            if detail.show:
                show = True
                break

        if show != result_obj.show:
            result_obj = result_obj.update(show = show)

        return result_obj


class GenericFileChangeProcessor(ActivityProcessor):
    """Class to process file changes based on git-status into activity detail records"""

    def process(self, result_obj: ActivityRecord, data: List[ExecutionData],
                status: Dict[str, Any], metadata: Dict[str, Any]) -> ActivityRecord:
        """Method to update a result object based on code and result data

        Args:
            result_obj(ActivityNote): An object containing the note
            data(list): A list of ExecutionData instances containing the data for this record
            status(dict): A dict containing the result of git status from gitlib
            metadata(str): A dictionary containing Dev Env specific or other developer defined data

        Returns:
            ActivityRecord
        """
        for cnt, filename in enumerate(status['untracked']):
            # skip any file in .git or .gigantum dirs
            if ".git" in filename or ".gigantum" in filename:
                continue

            activity_type, activity_detail_type, section = LabBook.infer_section_from_relative_path(filename)

            # We use a "private" attribute here, but it's better than the silent breakage that happened before
            # cf. https://github.com/gigantum/gigantum-client/issues/436
            if section == LabBook._default_activity_section:
                msg = f'Created new file `{filename}` in the Project Root. Note, it is best practice to use the Code, ' \
                    'Input, and Output sections exclusively. '
            else:
                msg = f"Created new {section} file `{filename}`"

            adr = ActivityDetailRecord(activity_detail_type,
                                       show=False,
                                       importance=max(255-cnt, 0),
                                       action=ActivityAction.CREATE,
                                       data=TextData('markdown', msg))

            result_obj = result_obj.add_detail_object(adr)

        cnt = 0
        for filename, change in status['unstaged']:
            # skip any file in .git or .gigantum dirs
            if ".git" in filename or ".gigantum" in filename:
                continue

            activity_type, activity_detail_type, section = LabBook.infer_section_from_relative_path(filename)

            if change == "deleted":
                action = ActivityAction.DELETE
            elif change == "added":
                action = ActivityAction.CREATE
            elif change == "modified":
                action = ActivityAction.EDIT
            elif change == "renamed":
                action = ActivityAction.EDIT
            else:
                action = ActivityAction.NOACTION

            adr_data = f"{change[0].upper() + change[1:]} {section} file `{filename}`"
            adr = ActivityDetailRecord(activity_detail_type,
                                       show=False,
                                       importance=max(255-cnt, 0),
                                       action=action,
                                       data=TextData('markdown', adr_data))

            result_obj = result_obj.add_detail_object(adr)
            cnt += 1

        return result_obj


class ActivityDetailLimitProcessor(ActivityProcessor):
    """Class to limit the number of captured detail records to 255 records + a truncation notification

    Since the "importance" value used to order detail records is 1 byte and a max value of 255, we'll truncate to
    255 records and insert a record indicating the truncation occurred
    """

    def process(self, result_obj: ActivityRecord, data: List[ExecutionData],
                status: Dict[str, Any], metadata: Dict[str, Any]) -> ActivityRecord:
        """Method to update a result object based on code and result data

        Args:
            result_obj(ActivityNote): An object containing the note
            data(list): A list of ExecutionData instances containing the data for this record
            status(dict): A dict containing the result of git status from gitlib
            metadata(str): A dictionary containing Dev Env specific or other developer defined data

        Returns:
            ActivityNote
        """
        orig_num = result_obj.num_detail_objects
        if result_obj.num_detail_objects > 255:
            result_obj = result_obj.trim_detail_objects(255)

            adr_data = (f"This activity produced {orig_num} detail records, "
                        f"but was truncated to the top 255 items. Inspect your code to make "
                        f"sure that this was not accidental. In Jupyter for example, you can"
                        f" use a `;` at the end of a line to suppress output from functions"
                        f" that print excessively.")

            adr = ActivityDetailRecord(ActivityDetailType.NOTE,
                                       show=True,
                                       importance=0,
                                       action=ActivityAction.NOACTION,
                                       data=TextData('markdown', adr_data))

            result_obj = result_obj.add_detail_object(adr)

        return result_obj

class ActivityDetailProgressProcessor(ActivityProcessor):
    """Class to search the current detailed objects and remove any that are the result of code that is
    rewriting the terminal screen (using control sequences)

    When such output is detected the last line of the output is saved, as it is the line that is typically
    left on the terminal when the code has finished
    """

    def process(self, result_obj: ActivityRecord, data: List[ExecutionData],
                status: Dict[str, Any], metadata: Dict[str, Any]) -> ActivityRecord:
        """Method to update a result object based on code and result data

        Args:
            result_obj(ActivityNote): An object containing the note
            data(list): A list of ExecutionData instances containing the data for this record
            status(dict): A dict containing the result of git status from gitlib
            metadata(str): A dictionary containing Dev Env specific or other developer defined data

        Returns:
            ActivityNote
        """
        detail_objects : List[ActivityDetailRecord] = []
        skip_line = True
        for obj in result_obj.detail_objects:
            if 'text/plain' in obj.data:
                text = obj.data['text/plain']
                if text.isspace():
                    # isspace() -> catch newlines
                    continue
                elif text[0] in ('\x1b', '\u001b'):
                    # 0x1b -> catch escape sequences
                    continue
                elif text[0] in ('\r', ) or text[0:2] in ('\n\r', ):
                    # \r -> handle when line is being rewritten
                    if skip_line and not text.isspace():
                        skip_line = False
                        if obj.show:
                            obj = obj.update(show=False)
                    else:
                        continue

            detail_objects.append(obj)

        return result_obj.update(detail_objects=DetailRecordList(detail_objects))
