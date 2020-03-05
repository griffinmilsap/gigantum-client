from typing import (Any, Dict, List)

from gtmcore.logging import LMLogger
from gtmcore.activity.processors.processor import ActivityProcessor, ExecutionData
from gtmcore.activity import ActivityRecord, ActivityDetailType, ActivityDetailRecord, ActivityAction
from gtmcore.activity.utils import ImmutableDict, ImmutableList, TextData

logger = LMLogger.get_logger()


class RStudioServerCodeProcessor(ActivityProcessor):
    """Class to process code records into activity detail records"""

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
        total_lines = 0
        # If there was some code, assume a cell was executed
        for cell_cnt, cell in enumerate(data):

            # in rstudio, multiple lines are spread across result entry.  Accumulate them.
            code_lines = []
            result_cnt = 0
            for result_entry in cell.code:
                entry_code = result_entry.get('code')
                if entry_code:
                    result_cnt += 1
                    total_lines += 1
                    code_lines.append(entry_code.strip())

            if code_lines:
                code_block = '\n'.join(code_lines)
                if "```" not in code_block:
                    # We only add code quotes if they aren't in there already
                    code_block = f"```\n{code_block}\n```"

                # Create detail record to capture executed code
                adr_code = ActivityDetailRecord(ActivityDetailType.CODE_EXECUTED,
                                                show=False,
                                                action=ActivityAction.EXECUTE,
                                                importance=max(255-result_cnt, 0),
                                                tags=ImmutableList(cell.tags),
                                                data=TextData('markdown', code_block))

                result_obj = result_obj.add_detail_object(adr_code)

        cell_str = f"{total_lines} lines" if cell_cnt > 1 else "code"
        result_obj = result_obj.update(message = f"Executed {cell_str} in {metadata['path']}")

        return result_obj


class RStudioServerPlaintextProcessor(ActivityProcessor):
    """Class to process plaintext result entries into activity detail records"""

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
        # Only store up to 64kB of plain text result data (if the user printed a TON don't save it all)
        truncate_at = 64 * 1000
        max_show_len = 280

        result_cnt = 0
        for cell in data:
            for result_entry in reversed(cell.result):
                if 'data' in result_entry:
                    if 'text/plain' in result_entry['data']:
                        text_data = result_entry['data']['text/plain']
                        if len(text_data) > 0:
                            if len(text_data) <= truncate_at:
                                adr_data = text_data
                            else:
                                adr_data = text_data[:truncate_at] + " ...\n\n <result truncated>"

                            adr = ActivityDetailRecord(ActivityDetailType.RESULT,
                                                       show=True if len(text_data) < max_show_len else False,
                                                       action=ActivityAction.CREATE,
                                                       importance=max(255-result_cnt-100, 0),
                                                       tags=ImmutableList(cell.tags),
                                                       data=TextData('plain', adr_data))

                            result_obj = result_obj.add_detail_object(adr)

                            result_cnt += 1

        return result_obj


class RStudioServerImageExtractorProcessor(ActivityProcessor):
    """Class to perform image extraction for RStudioServer activity"""

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
        supported_image_types = ['image/png', 'image/jpeg', 'image/jpg', 'image/gif', 'image/bmp']

        # If a supported image exists in the result, grab it and create a detail record
        result_cnt = 0
        for cell in data:
            for result_entry in reversed(cell.result):
                if 'data' in result_entry:
                    for mime_type in result_entry['data']:
                        if mime_type in supported_image_types:
                            # You got an image

                            # All RStudio responses should contain decoded strings, even b64encoded data
                            strdata = result_entry['data'][mime_type]

                            adr_img = ActivityDetailRecord(ActivityDetailType.RESULT,
                                                           show=True,
                                                           action=ActivityAction.CREATE,
                                                           importance=max(255-result_cnt, 0),
                                                           tags=ImmutableList(cell.tags),
                                                           data=ImmutableDict({mime_type: strdata}))

                            result_obj = result_obj.add_detail_object(adr_img)

                            # Set Activity Record Message
                            msg = f"Executed in {metadata['path']} and generated a result"
                            result_obj = result_obj.update(message = msg)

                            result_cnt += 1

        return result_obj
