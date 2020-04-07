from typing import (Any, Dict, List)

from gtmcore.logging import LMLogger
from gtmcore.activity.processors.processor import ActivityProcessor, ExecutionData
from gtmcore.activity import ActivityRecord, ActivityDetailType, ActivityDetailRecord, ActivityAction

import json
import requests

from gtmcore.configuration import Configuration

logger = LMLogger.get_logger()

class ElevatorProcessor(ActivityProcessor):
    """Class that sends cell data to ELEVATOR
        Note that user must already be added to db
    """

    def __init__(self, config_file: str=None) -> None:
        """Constructor

        Args:
            config_file(str): Optional config file location if don't want to load from default location
        """
        self.config = Configuration(config_file=config_file)
        self.elevator_host = self.config.config['elevator']['host']
        self.elevator_port = self.config.config['elevator']['port']
        self.elevator_url = f'http://{self.elevator_host}:{self.elevator_port}'

        # Get a list of enrolled users so we know how to send cell info
        self.people_ids = None
        try:
            req = requests.get(self.elevator_url + '/api/people')
            people = json.loads(req.text)
            self.people_ids = { p['username']: p['person_id'] for p in people }
        except:
            logger.info("Elevator service unreachable, not logging cells")

    def process(self, result_obj: ActivityRecord, data: List[ExecutionData],
                status: Dict[str, Any], metadata: Dict[str, Any]) -> ActivityRecord:

        username = metadata.get('user')
        person_id = None if self.people_ids is None else self.people_ids.get(username)
        if person_id is not None: 
            cell_loc = f'{self.elevator_url}/api/people/{person_id}/cells'

            try: 
                for block in data:
                    code_data = '\n'.join([c.get('code', '') for c in reversed(block.code)])
                    cell_data = dict( 
                        code = code_data, 
                        result = "", 
                        error = block.cell_error)
                    req = requests.post(cell_loc, json=cell_data)
            except Exception as e:
                logger.info( repr( e ) )

        return result_obj


