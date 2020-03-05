import logging
import uuid
from typing import (Any, Dict, List)

from gtmcore.activity.tests.fixtures import redis_client
from gtmcore.fixtures import mock_labbook

from gtmcore.activity import ActivityType, ActivityRecord
from gtmcore.activity.monitors.activity import ActivityMonitor
from gtmcore.activity.processors.processor import ActivityProcessor, ExecutionData

class ProblemProcessor(ActivityProcessor):
    def process(self, result_obj: ActivityRecord, data: List[ExecutionData], status: Dict[str, Any],
                metadata: Dict[str, Any]) -> ActivityRecord:
        raise Exception("This should be handled")

class BasicProcessor(ActivityProcessor):
    def process(self, result_obj: ActivityRecord, data: List[ExecutionData], status: Dict[str, Any],
                metadata: Dict[str, Any]) -> ActivityRecord:
        return result_obj.update(message = 'Status Message')


class TestActivityMonitor(object):
    def test_processor_exception(self, redis_client, mock_labbook, caplog):
        caplog.set_level(logging.INFO, logger='labmanager')

        monitor_key = "dev_env_monitor:{}:{}:{}:{}:activity_monitor:{}".format('test',
                                                                               'test',
                                                                               'labbook1',
                                                                               'jupyterlab-ubuntu1604',
                                                                               uuid.uuid4())
        monitor = ActivityMonitor('test',
                                  'test',
                                  mock_labbook[2].name,
                                  monitor_key,
                                  config_file=mock_labbook[0])

        monitor.add_processor(ProblemProcessor())
        monitor.add_processor(BasicProcessor())

        ar = monitor.process(ActivityType.CODE,
                             data=[ExecutionData()],
                             metadata={})

        # DP NOTE: caplog is only captures logs for the root logger, and doesn't
        #          contain messages from the labmanager log
        #assert 'problem executing processor ProblemProcessor' in caplog.record_tuples[-1][2]

        assert ar.message == "Status Message"
