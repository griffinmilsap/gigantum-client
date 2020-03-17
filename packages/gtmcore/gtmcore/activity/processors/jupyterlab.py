import re
from typing import (Any, Dict, List)

from gtmcore.logging import LMLogger
from gtmcore.activity.processors.processor import ActivityProcessor, ExecutionData
from gtmcore.activity import ActivityRecord, ActivityDetailType, ActivityDetailRecord, ActivityAction
from gtmcore.activity.utils import ImmutableDict, ImmutableList, TextData

logger = LMLogger.get_logger()


class JupyterLabCellVisibilityProcessor(ActivityProcessor):
    """Class to set visibility in activity record based on cell metadata

    Currently, 4 variations on tracking metadata can be set:
      - auto
      - show
      - hide
      - ignore
    """

    # This is actually fairly permissive - the comment can be anywhere and we're not fussy about whitespace
    # We'll only get the first one below
    comment_re = re.compile(r'# *gtm:(\w+)')

    def process(self, result_obj: ActivityRecord, data: List[ExecutionData],
                status: Dict[str, Any], metadata: Dict[str, Any]) -> ActivityRecord:
        tags = {}
        for idx, detail in enumerate(result_obj.detail_objects):
            if detail.type is ActivityDetailType.CODE_EXECUTED:
                code = detail.data['text/markdown']
                res = self.comment_re.search(code)
                if res:
                    directive = res[1]
                    if directive == 'auto':
                        # This is the default behavior
                        pass
                    elif directive in ['show', 'hide', 'ignore']:
                        for tag in detail.tags:
                            # currently, the 'ex1' type tags are the only ones...
                            if tag.startswith('ex'):
                                tags[tag] = directive
                    else:
                        # We have encountered an unknown comment directive.
                        logger.warning(f'Encountered unknown comment directive gtm:{directive}')
                        pass

        if tags:
            result_obj = result_obj.set_visibility(tags)

        return result_obj


class JupyterLabCodeProcessor(ActivityProcessor):
    """Class to process code records into activity detail records"""

    def process(self, result_obj: ActivityRecord, data: List[ExecutionData],
                status: Dict[str, Any], metadata: Dict[str, Any]) -> ActivityRecord:
        """Method to update a result object based on code and result data

        Args:
            result_obj: An object containing the note
            data: A list of ExecutionData instances containing the data for this record
            status: A dict containing the result of git status from gitlib
            metadata: A dictionary containing Dev Env specific or other developer defined data

        Returns:
            ActivityRecord with code details
        """
        # If there was some code, assume a cell was executed
        result_cnt = 0
        for cell_cnt, cell in enumerate(data):
            for result_entry in reversed(cell.code):
                if result_entry.get('code'):
                    # Create detail record to capture executed code
                    adr_data = f"```\n{result_entry.get('code')}\n```"
                    adr_code = ActivityDetailRecord(ActivityDetailType.CODE_EXECUTED,
                                                    show=False,
                                                    action=ActivityAction.EXECUTE,
                                                    importance=max(255-result_cnt, 0),
                                                    tags=ImmutableList(cell.tags),
                                                    data=TextData('markdown', adr_data))

                    result_obj = result_obj.add_detail_object(adr_code)

                    result_cnt += 1

        # Set Activity Record Message
        cell_str = f"{cell_cnt} cells" if cell_cnt > 1 else "cell"
        result_obj = result_obj.update(message = f"Executed {cell_str} in notebook {metadata['path']}")

        return result_obj


class JupyterLabPlaintextProcessor(ActivityProcessor):
    """Class to process plaintext result entries into activity detail records"""

    def process(self, result_obj: ActivityRecord, data: List[ExecutionData],
                status: Dict[str, Any], metadata: Dict[str, Any]) -> ActivityRecord:
        """Method to update a result object based on code and result data

        Args:
            result_obj: An object containing the note
            data: A list of ExecutionData instances containing the data for this record
            status: A dict containing the result of git status from gitlib
            metadata: A dictionary containing Dev Env specific or other developer defined data

        Returns:
            ActivityRecord with displayed text details
        """
        # Only store up to 64kB of plain text result data (if the user printed a TON don't save it all)
        truncate_at = 64 * 1000
        max_show_len = 280

        result_cnt = 0
        for cell in data:
            for result_entry in reversed(cell.result):
                if 'metadata' in result_entry:
                    if 'source' in result_entry['metadata']:
                        if result_entry['metadata']['source'] == "display_data":
                            # Don't save plain-text representations of displayed data by default.
                            continue

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


class JupyterLabImageExtractorProcessor(ActivityProcessor):
    """Class to perform image extraction for JupyterLab activity"""

    def process(self, result_obj: ActivityRecord, data: List[ExecutionData],
                status: Dict[str, Any], metadata: Dict[str, Any]) -> ActivityRecord:
        """Method to update a result object based on code and result data

        Args:
            result_obj: An object containing the note
            data: A list of ExecutionData instances containing the data for this record
            status: A dict containing the result of git status from gitlib
            metadata: A dictionary containing Dev Env specific or other developer defined data

        Returns:
            ActivityRecord with image details
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
                            adr_img = ActivityDetailRecord(ActivityDetailType.RESULT,
                                                           show=True,
                                                           action=ActivityAction.CREATE,
                                                           importance=max(255-result_cnt, 0),
                                                           tags=ImmutableList(cell.tags),
                                                           data=ImmutableDict({mime_type: result_entry['data'][mime_type]}))

                            result_obj = result_obj.add_detail_object(adr_img)

                            # Set Activity Record Message
                            msg = f"Executed cell in notebook {metadata['path']} and generated a result"
                            result_obj = result_obj.update(message = msg)

                            result_cnt += 1

        return result_obj
