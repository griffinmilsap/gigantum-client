from gtmcore.activity.processors.jupyterlab import JupyterLabCellVisibilityProcessor
from gtmcore.activity.tests.fixtures import redis_client, mock_kernel
from gtmcore.fixtures import mock_labbook
import uuid
import os

from gtmcore.activity.monitors.monitor_jupyterlab import JupyterLabNotebookMonitor, JupyterLabCodeProcessor, \
    JupyterLabPlaintextProcessor, JupyterLabImageExtractorProcessor
from gtmcore.activity.processors.core import ActivityShowBasicProcessor, GenericFileChangeProcessor, \
    ActivityDetailLimitProcessor, ActivityDetailProgressProcessor
from gtmcore.activity import ActivityStore, ActivityType, ActivityDetailType


class TestJupyterLabNotebookMonitor(object):

    def test_init(self, redis_client, mock_labbook):
        """Test getting the supported names of the dev env monitor"""
        # Create dummy file in lab book
        dummy_file = os.path.join(mock_labbook[2].root_dir, 'Test.ipynb')
        with open(dummy_file, 'wt') as tf:
            tf.write("Dummy file")

        monitor_key = "dev_env_monitor:{}:{}:{}:{}:activity_monitor:{}".format('test',
                                                                               'test',
                                                                               'labbook1',
                                                                               'jupyterlab-ubuntu1604',
                                                                               uuid.uuid4())

        monitor = JupyterLabNotebookMonitor("test", "test", mock_labbook[2].name,
                                            monitor_key, config_file=mock_labbook[0])

        assert len(monitor.processors) == 8
        assert type(monitor.processors[0]) == JupyterLabCodeProcessor
        assert type(monitor.processors[1]) == GenericFileChangeProcessor
        assert type(monitor.processors[2]) == JupyterLabPlaintextProcessor
        assert type(monitor.processors[3]) == JupyterLabImageExtractorProcessor
        assert type(monitor.processors[4]) == JupyterLabCellVisibilityProcessor
        assert type(monitor.processors[5]) == ActivityDetailProgressProcessor
        assert type(monitor.processors[6]) == ActivityDetailLimitProcessor
        assert type(monitor.processors[7]) == ActivityShowBasicProcessor

    def test_start(self, redis_client, mock_labbook, mock_kernel):
        """Test processing notebook activity"""
        dummy_file = os.path.join(mock_labbook[2].root_dir, 'code', 'Test.ipynb')
        with open(dummy_file, 'wt') as tf:
            tf.write("Dummy file")

        monitor_key = "dev_env_monitor:{}:{}:{}:{}:activity_monitor:{}".format('test',
                                                                               'test',
                                                                               'labbook1',
                                                                               'jupyterlab-ubuntu1604',
                                                                               uuid.uuid4())

        monitor = JupyterLabNotebookMonitor("test", "test", mock_labbook[2].name,
                                            monitor_key, config_file=mock_labbook[0])

        # Setup monitoring metadata
        metadata = {"kernel_id": "XXXX",
                    "kernel_name": 'python',
                    "kernel_type": 'notebook',
                    "path": 'code/Test.ipynb'}

        # Perform an action
        mock_kernel[0].execute("print('Hello, World')")

        # Check lab book repo state
        status = mock_labbook[2].git.status()
        assert len(status["untracked"]) == 1
        assert status["untracked"][0] == 'code/Test.ipynb'

        # Process messages
        msg1 = mock_kernel[0].get_iopub_msg()
        msg2 = mock_kernel[0].get_iopub_msg()
        msg3 = mock_kernel[0].get_iopub_msg()
        msg4 = mock_kernel[0].get_iopub_msg()

        # Process first state change message
        assert monitor.kernel_status == 'idle'
        assert monitor.can_store_activity_record is False
        monitor.handle_message(msg1)
        assert monitor.kernel_status == 'busy'

        # Process input message
        monitor.handle_message(msg2)
        assert len(monitor.current_cell.code) > 0
        assert len(monitor.cell_data) == 0
        assert monitor.can_store_activity_record is False

        # Process output message
        monitor.handle_message(msg3)
        assert len(monitor.current_cell.result) > 0
        assert len(monitor.cell_data) == 0
        assert monitor.can_store_activity_record is False

        # Check lab book repo state
        status = mock_labbook[2].git.status()
        assert len(status["untracked"]) == 1
        assert status["untracked"][0] == 'code/Test.ipynb'

        # Process final state change message
        monitor.handle_message(msg4)
        assert monitor.kernel_status == 'idle'
        assert monitor.can_store_activity_record is True
        assert len(monitor.cell_data) == 1

        # Store the record manually for this test
        monitor.store_record(metadata)
        assert monitor.can_store_activity_record is False
        assert len(monitor.cell_data) == 0

        # Check lab book repo state
        status = mock_labbook[2].git.status()
        assert len(status["untracked"]) == 0
        assert len(status["staged"]) == 0
        assert len(status["unstaged"]) == 0

        # Check activity entry
        log = mock_labbook[2].git.log()
        assert len(log) == 4
        assert 'code/Test.ipynb' in log[0]['message']

        a_store = ActivityStore(mock_labbook[2])
        record = a_store.get_activity_record(log[0]['commit'])
        assert record.type == ActivityType.CODE
        assert record.show is True
        assert record.importance == 0
        assert not record.tags
        assert record.message == 'Executed cell in notebook code/Test.ipynb'
        assert len(record.detail_objects) == 3
        assert record.detail_objects[0].show is True
        assert record.detail_objects[0].type.value == ActivityDetailType.RESULT.value
        assert record.detail_objects[0].importance == 155
        assert record.detail_objects[1].show is False
        assert record.detail_objects[1].type.value == ActivityDetailType.CODE.value
        assert record.detail_objects[1].importance == 255
        assert record.detail_objects[2].show is False
        assert record.detail_objects[2].type.value == ActivityDetailType.CODE_EXECUTED.value
        assert record.detail_objects[2].importance == 255

    def test_start_modify(self, redis_client, mock_labbook, mock_kernel):
        """Test processing notebook activity and have it modify an existing file & create some files"""
        dummy_file = os.path.join(mock_labbook[2].root_dir, 'code', 'Test.ipynb')
        dummy_output = os.path.join(mock_labbook[2].root_dir, 'output', 'result.bin')
        with open(dummy_file, 'wt') as tf:
            tf.write("Dummy file")

        monitor_key = "dev_env_monitor:{}:{}:{}:{}:activity_monitor:{}".format('test',
                                                                               'test',
                                                                               'labbook1',
                                                                               'jupyterlab-ubuntu1604',
                                                                               uuid.uuid4())

        monitor = JupyterLabNotebookMonitor("test", "test", mock_labbook[2].name,
                                            monitor_key, config_file=mock_labbook[0])

        # Setup monitoring metadata
        metadata = {"kernel_id": "XXXX",
                    "kernel_name": 'python',
                    "kernel_type": 'notebook',
                    "path": 'code/Test.ipynb'}

        # Perform an action
        mock_kernel[0].execute("print('Hello, World')")

        # Check lab book repo state
        status = mock_labbook[2].git.status()
        assert len(status["untracked"]) == 1
        assert status["untracked"][0] == 'code/Test.ipynb'

        # Process messages
        msg1 = mock_kernel[0].get_iopub_msg()
        msg2 = mock_kernel[0].get_iopub_msg()
        msg3 = mock_kernel[0].get_iopub_msg()
        msg4 = mock_kernel[0].get_iopub_msg()

        # Process first state change message
        assert monitor.kernel_status == 'idle'
        assert monitor.can_store_activity_record is False
        monitor.handle_message(msg1)
        assert monitor.kernel_status == 'busy'

        # Process input message
        monitor.handle_message(msg2)
        assert len(monitor.current_cell.code) > 0
        assert len(monitor.cell_data) == 0
        assert monitor.can_store_activity_record is False

        # Process output message
        monitor.handle_message(msg3)
        assert len(monitor.current_cell.result) > 0
        assert len(monitor.cell_data) == 0
        assert monitor.can_store_activity_record is False

        # Check lab book repo state
        status = mock_labbook[2].git.status()
        assert len(status["untracked"]) == 1
        assert status["untracked"][0] == 'code/Test.ipynb'

        # Process final state change message
        monitor.handle_message(msg4)
        assert monitor.kernel_status == 'idle'
        assert monitor.can_store_activity_record is True
        assert len(monitor.cell_data) == 1

        # Store the record manually for this test
        monitor.store_record(metadata)
        assert monitor.can_store_activity_record is False
        assert len(monitor.cell_data) == 0

        # Check lab book repo state
        status = mock_labbook[2].git.status()
        assert len(status["untracked"]) == 0
        assert len(status["staged"]) == 0
        assert len(status["unstaged"]) == 0

        # Check activity entry
        log = mock_labbook[2].git.log()
        assert len(log) == 4
        assert 'code/Test.ipynb' in log[0]['message']

        # Mock Performing an action AGAIN, faking editing the file and generating some output files
        mock_kernel[0].execute("a=100\nprint('Hello, World 2')")
        with open(dummy_file, 'wt') as tf:
            tf.write("change the fake notebook")

        with open(dummy_output, 'wt') as tf:
            tf.write("some result data")
        # Process messages
        msg1 = mock_kernel[0].get_iopub_msg()
        msg2 = mock_kernel[0].get_iopub_msg()
        msg3 = mock_kernel[0].get_iopub_msg()
        msg4 = mock_kernel[0].get_iopub_msg()

        # Process first state change message
        assert monitor.kernel_status == 'idle'
        assert monitor.can_store_activity_record is False
        monitor.handle_message(msg1)
        assert monitor.kernel_status == 'busy'

        # Process input message
        monitor.handle_message(msg2)
        assert len(monitor.current_cell.code) > 0
        assert len(monitor.cell_data) == 0
        assert monitor.can_store_activity_record is False

        # Process output message
        monitor.handle_message(msg3)
        assert len(monitor.current_cell.result) > 0
        assert len(monitor.cell_data) == 0
        assert monitor.can_store_activity_record is False

        # Check lab book repo state
        status = mock_labbook[2].git.status()
        assert len(status["staged"]) == 0
        assert len(status["untracked"]) == 1
        assert len(status["unstaged"]) == 1
        assert status["unstaged"][0][0] == 'code/Test.ipynb'
        assert status["unstaged"][0][1] == 'modified'

        # Process final state change message
        monitor.handle_message(msg4)
        assert monitor.kernel_status == 'idle'
        assert monitor.can_store_activity_record is True
        assert len(monitor.cell_data) == 1

        # Store the record manually for this test
        monitor.store_record(metadata)
        assert monitor.can_store_activity_record is False
        assert len(monitor.cell_data) == 0

        # Check lab book repo state
        status = mock_labbook[2].git.status()
        assert len(status["untracked"]) == 0
        assert len(status["staged"]) == 0
        assert len(status["unstaged"]) == 0

        # Check activity entry
        log = mock_labbook[2].git.log()
        assert len(log) == 6
        assert 'code/Test.ipynb' in log[0]['message']

        a_store = ActivityStore(mock_labbook[2])
        record = a_store.get_activity_record(log[0]['commit'])
        assert record.type == ActivityType.CODE
        assert record.show is True
        assert record.importance == 0
        assert not record.tags
        assert record.message == 'Executed cell in notebook code/Test.ipynb'
        assert len(record.detail_objects) == 4
        assert record.detail_objects[0].show is True
        assert record.detail_objects[0].type.value == ActivityDetailType.RESULT.value
        assert record.detail_objects[0].importance == 155
        assert record.detail_objects[1].show is False
        assert record.detail_objects[1].type.value == ActivityDetailType.CODE.value
        assert record.detail_objects[1].importance == 255
        assert record.detail_objects[2].show is False
        assert record.detail_objects[2].type.value == ActivityDetailType.CODE_EXECUTED.value
        assert record.detail_objects[2].importance == 255
        assert record.detail_objects[3].show is False
        assert record.detail_objects[3].type.value == ActivityDetailType.OUTPUT_DATA.value
        assert record.detail_objects[3].importance == 255

        detail = a_store.get_detail_record(record.detail_objects[3].key)
        assert len(detail.data) == 1
        assert detail.data['text/markdown'] == 'Created new Output Data file `output/result.bin`'

        detail = a_store.get_detail_record(record.detail_objects[1].key)
        assert len(detail.data) == 1
        assert detail.data['text/markdown'] == 'Modified Code file `code/Test.ipynb`'

    def test_no_show(self, redis_client, mock_labbook, mock_kernel):
        """Test processing notebook activity that doesn't have any important detail items"""
        monitor_key = "dev_env_monitor:{}:{}:{}:{}:activity_monitor:{}".format('test',
                                                                               'test',
                                                                               'labbook1',
                                                                               'jupyterlab-ubuntu1604',
                                                                               uuid.uuid4())

        monitor = JupyterLabNotebookMonitor("test", "test", mock_labbook[2].name,
                                            monitor_key, config_file=mock_labbook[0])

        # Setup monitoring metadata
        metadata = {"kernel_id": "XXXX",
                    "kernel_name": 'python',
                    "kernel_type": 'notebook',
                    "path": 'code/Test.ipynb'}

        # Perform an action
        mock_kernel[0].execute("a=1")

        # Check lab book repo state
        status = mock_labbook[2].git.status()
        assert len(status["untracked"]) == 0

        # Process messages
        msg1 = mock_kernel[0].get_iopub_msg()
        msg2 = mock_kernel[0].get_iopub_msg()
        msg3 = mock_kernel[0].get_iopub_msg()

        # Process first state change message
        assert monitor.kernel_status == 'idle'
        assert monitor.can_store_activity_record is False
        monitor.handle_message(msg1)
        assert monitor.kernel_status == 'busy'

        # Process input message
        monitor.handle_message(msg2)
        assert len(monitor.current_cell.code) > 0
        assert len(monitor.cell_data) == 0
        assert monitor.can_store_activity_record is False

        # Process output message
        monitor.handle_message(msg3)
        assert monitor.kernel_status == 'idle'
        assert monitor.can_store_activity_record is True
        assert len(monitor.cell_data) == 1

        # Store the record manually for this test
        monitor.store_record(metadata)
        assert monitor.can_store_activity_record is False
        assert len(monitor.cell_data) == 0

        # Check activity entry
        log = mock_labbook[2].git.log()
        assert len(log) == 4
        assert 'code/Test.ipynb' in log[0]['message']

        a_store = ActivityStore(mock_labbook[2])
        record = a_store.get_activity_record(log[0]['commit'])
        assert record.type == ActivityType.CODE
        assert record.show is False
        assert record.importance == 0
        assert not record.tags
        assert record.message == 'Executed cell in notebook code/Test.ipynb'
        assert len(record.detail_objects) == 1
        assert record.detail_objects[0].show is False
        assert record.detail_objects[0].type.value == ActivityDetailType.CODE_EXECUTED.value
        assert record.detail_objects[0].importance == 255

    def test_gtm_comments(self, redis_client, mock_labbook, mock_kernel):
        """Test processing notebook activity that's modified by gtm: comments

        Testing here is lighter than above - we only test aspects relevant to
        showing / hiding/ ignoring"""
        monitor_key = "dev_env_monitor:{}:{}:{}:{}:activity_monitor:{}".format('test',
                                                                               'test',
                                                                               'labbook1',
                                                                               'jupyterlab-ubuntu1604',
                                                                               uuid.uuid4())

        monitor = JupyterLabNotebookMonitor("test", "test", mock_labbook[2].name,
                                            monitor_key, config_file=mock_labbook[0])

        # Setup monitoring metadata
        metadata = {"kernel_id": "XXXX",
                    "kernel_name": 'python',
                    "kernel_type": 'notebook',
                    "path": 'code/Test.ipynb'}

        # We'll use this repeatedly below
        a_store = ActivityStore(mock_labbook[2])

        # First, we check both cases for the default (auto)
        # Perform an action that generates output (default shown)
        mock_kernel[0].execute("# gtm:auto\nprint('Hello!')")

        # Process messages
        for _ in range(4):
            monitor.handle_message(mock_kernel[0].get_iopub_msg())

        # This is the one redundant assertion with other tests in this file (and it's repeated in each execution below),
        # but it's fairly central to what we're doing!
        assert monitor.can_store_activity_record is True

        # Store the record manually for this test
        monitor.store_record(metadata)

        # Check activity entry
        log = mock_labbook[2].git.log()

        record = a_store.get_activity_record(log[0]['commit'])
        assert record.show is True

        # Perform an action that doesn't generate output (default hidden)
        mock_kernel[0].execute("# gtm:auto\na=1")

        # Process messages
        for _ in range(3):
            monitor.handle_message(mock_kernel[0].get_iopub_msg())

        assert monitor.can_store_activity_record is True

        # Store the record manually for this test
        monitor.store_record(metadata)

        # Check activity entry
        log = mock_labbook[2].git.log()

        record = a_store.get_activity_record(log[0]['commit'])
        assert record.show is False

        # Perform an action that generates output (default shown)
        # Hide comment should override
        mock_kernel[0].execute("# gtm:hide\nprint('Hello!')")

        # Process messages
        for _ in range(4):
            monitor.handle_message(mock_kernel[0].get_iopub_msg())

        assert monitor.can_store_activity_record is True

        # Store the record manually for this test
        monitor.store_record(metadata)

        # Check activity entry
        log = mock_labbook[2].git.log()

        record = a_store.get_activity_record(log[0]['commit'])
        assert record.show is False

        # Perform an action that doesn't generate output (default hidden)
        # Show comment should override
        mock_kernel[0].execute("# gtm:show\na=1")

        # Process messages
        for _ in range(3):
            monitor.handle_message(mock_kernel[0].get_iopub_msg())

        assert monitor.can_store_activity_record is True

        # Store the record manually for this test
        monitor.store_record(metadata)

        # Check activity entry
        log = mock_labbook[2].git.log()

        record = a_store.get_activity_record(log[0]['commit'])
        assert record.show is True

        # Finally, we test the ignore feature
        # Here, the default shouldn't matter - we shouldn't end up with a new record
        # Show comment should override
        mock_kernel[0].execute("# gtm:ignore\na=1")

        # Process messages
        for _ in range(3):
            monitor.handle_message(mock_kernel[0].get_iopub_msg())

        assert monitor.can_store_activity_record is True

        # Store the record manually for this test
        monitor.store_record(metadata)

        # Check activity entry
        log = mock_labbook[2].git.log()

        record = a_store.get_activity_record(log[0]['commit'])
        # assert there is "nothing" in the activity record (we still generated one)
        print(record)
        for elm in record.detail_objects:
            print("\t", elm.tags)
        assert record.num_detail_objects == 0

    def test_add_many_files(self, redis_client, mock_labbook, mock_kernel):
        """Test processing notebook activity when lots of output files have been created"""
        for file_number in range(0, 260):
            with open(os.path.join(mock_labbook[2].root_dir, 'output', f"{file_number}.dat"), 'wt') as tf:
                tf.write("blah")

        monitor_key = "dev_env_monitor:{}:{}:{}:{}:activity_monitor:{}".format('test',
                                                                               'test',
                                                                               'labbook1',
                                                                               'jupyterlab-ubuntu1604',
                                                                               uuid.uuid4())

        monitor = JupyterLabNotebookMonitor("test", "test", mock_labbook[2].name,
                                            monitor_key, config_file=mock_labbook[0])

        # Setup monitoring metadata
        metadata = {"kernel_id": "XXXX",
                    "kernel_name": 'python',
                    "kernel_type": 'notebook',
                    "path": 'code/Test.ipynb'}

        # Perform an action
        mock_kernel[0].execute("print('Generated 260 output files')")

        # Check lab book repo state
        status = mock_labbook[2].git.status()
        assert len(status["untracked"]) == 260

        # Process messages
        msg1 = mock_kernel[0].get_iopub_msg()
        msg2 = mock_kernel[0].get_iopub_msg()
        msg3 = mock_kernel[0].get_iopub_msg()
        msg4 = mock_kernel[0].get_iopub_msg()

        # Process first state change message
        assert monitor.kernel_status == 'idle'
        assert monitor.can_store_activity_record is False
        monitor.handle_message(msg1)
        assert monitor.kernel_status == 'busy'

        # Process input message
        monitor.handle_message(msg2)
        assert len(monitor.current_cell.code) > 0
        assert len(monitor.cell_data) == 0
        assert monitor.can_store_activity_record is False

        # Process output message
        monitor.handle_message(msg3)
        assert len(monitor.current_cell.result) > 0
        assert len(monitor.cell_data) == 0
        assert monitor.can_store_activity_record is False

        # Process final state change message
        monitor.handle_message(msg4)
        assert monitor.kernel_status == 'idle'
        assert monitor.can_store_activity_record is True
        assert len(monitor.cell_data) == 1

        # Store the record manually for this test
        monitor.store_record(metadata)
        assert monitor.can_store_activity_record is False
        assert len(monitor.cell_data) == 0

        # Check lab book repo state
        status = mock_labbook[2].git.status()
        assert len(status["untracked"]) == 0
        assert len(status["staged"]) == 0
        assert len(status["unstaged"]) == 0

        # Check activity entry
        log = mock_labbook[2].git.log()
        assert len(log) == 4
        assert 'code/Test.ipynb' in log[0]['message']

        a_store = ActivityStore(mock_labbook[2])
        record = a_store.get_activity_record(log[0]['commit'])
        assert record.type == ActivityType.CODE
        assert record.show is True
        assert record.importance == 0
        assert not record.tags
        assert record.message == 'Executed cell in notebook code/Test.ipynb'
        assert len(record.detail_objects) == 256
        assert record.num_detail_objects == 256
        assert record.detail_objects[0].show is True
        assert record.detail_objects[0].type.value == ActivityDetailType.NOTE.value
        assert record.detail_objects[0].importance == 0
        assert record.detail_objects[1].show is True
        assert record.detail_objects[1].type.value == ActivityDetailType.RESULT.value
        assert record.detail_objects[1].importance == 155
        assert record.detail_objects[2].show is False
        assert record.detail_objects[2].type.value == ActivityDetailType.CODE_EXECUTED.value
        assert record.detail_objects[2].importance == 255
        assert record.detail_objects[3].show is False
        assert record.detail_objects[3].type.value == ActivityDetailType.OUTPUT_DATA.value
        assert record.detail_objects[3].importance == 255
        assert record.detail_objects[4].show is False
        assert record.detail_objects[4].type.value == ActivityDetailType.OUTPUT_DATA.value
        assert record.detail_objects[4].importance == 254
        assert record.detail_objects[48].show is False
        assert record.detail_objects[48].type.value == ActivityDetailType.OUTPUT_DATA.value
        assert record.detail_objects[48].importance == 210
        assert record.detail_objects[254].show is False
        assert record.detail_objects[254].type.value == ActivityDetailType.OUTPUT_DATA.value
        assert record.detail_objects[254].importance == 4
        assert record.detail_objects[255].show is False
        assert record.detail_objects[255].type.value == ActivityDetailType.OUTPUT_DATA.value
        assert record.detail_objects[255].importance == 3

    def test_no_record_on_error(self, redis_client, mock_labbook, mock_kernel):
        """Test processing notebook activity that didn't execute successfully"""
        monitor_key = "dev_env_monitor:{}:{}:{}:{}:activity_monitor:{}".format('test',
                                                                               'test',
                                                                               'labbook1',
                                                                               'jupyterlab-ubuntu1604',
                                                                               uuid.uuid4())

        monitor = JupyterLabNotebookMonitor("test", "test", mock_labbook[2].name,
                                            monitor_key, config_file=mock_labbook[0])

        log = mock_labbook[2].git.log()
        assert len(log) == 2

        # Setup monitoring metadata
        metadata = {"kernel_id": "XXXX",
                    "kernel_name": 'python',
                    "kernel_type": 'notebook',
                    "path": 'code/Test.ipynb'}

        # Perform an action
        mock_kernel[0].execute("1/0")

        # Check lab book repo state
        status = mock_labbook[2].git.status()
        assert len(status["untracked"]) == 0

        # Process messages
        msg1 = mock_kernel[0].get_iopub_msg()
        msg2 = mock_kernel[0].get_iopub_msg()
        msg3 = mock_kernel[0].get_iopub_msg()
        msg4 = mock_kernel[0].get_iopub_msg()
        print(msg3)
        print(msg4)

        # Process first state change message
        assert monitor.kernel_status == 'idle'
        assert monitor.can_store_activity_record is False
        monitor.handle_message(msg1)
        assert monitor.kernel_status == 'busy'

        # Process input message
        monitor.handle_message(msg2)
        assert len(monitor.current_cell.code) > 0
        assert len(monitor.cell_data) == 0
        assert monitor.current_cell.cell_error is False
        assert monitor.can_store_activity_record is False

        # Process output message
        monitor.handle_message(msg3)
        assert len(monitor.current_cell.result) == 0
        assert monitor.current_cell.cell_error is True
        assert len(monitor.cell_data) == 0
        assert monitor.can_store_activity_record is False

        # Process final state change message
        monitor.handle_message(msg4)
        assert monitor.kernel_status == 'idle'
        assert monitor.can_store_activity_record is True
        assert len(monitor.cell_data) == 0
        assert len(monitor.current_cell.code) == 0
        assert len(monitor.current_cell.result) == 0

        # Store the record manually for this test
        monitor.store_record(metadata)
        assert monitor.can_store_activity_record is False
        assert len(monitor.cell_data) == 0

        # Check activity entry
        log = mock_labbook[2].git.log()

        # log should not increment because of error
        assert len(log) == 2
        assert 'GTM' not in log[0]['message']

    def test_multiple_cells(self, redis_client, mock_labbook, mock_kernel):
        """Test processing notebook activity"""
        dummy_file = os.path.join(mock_labbook[2].root_dir, 'code', 'Test.ipynb')
        with open(dummy_file, 'wt') as tf:
            tf.write("Dummy file")

        monitor_key = "dev_env_monitor:{}:{}:{}:{}:activity_monitor:{}".format('test',
                                                                               'test',
                                                                               'labbook1',
                                                                               'jupyterlab-ubuntu1604',
                                                                               uuid.uuid4())

        monitor = JupyterLabNotebookMonitor("test", "test", mock_labbook[2].name,
                                            monitor_key, config_file=mock_labbook[0])

        # Setup monitoring metadata
        metadata = {"kernel_id": "XXXX",
                    "kernel_name": 'python',
                    "kernel_type": 'notebook',
                    "path": 'code/Test.ipynb'}

        # Perform an action
        mock_kernel[0].execute("print('Hello, World')")
        mock_kernel[0].execute("print('Cell number 2!')")

        # Check lab book repo state
        status = mock_labbook[2].git.status()
        assert len(status["untracked"]) == 1
        assert status["untracked"][0] == 'code/Test.ipynb'

        # Process messages
        msg1a = mock_kernel[0].get_iopub_msg()
        msg2a = mock_kernel[0].get_iopub_msg()
        msg3a = mock_kernel[0].get_iopub_msg()
        msg4a = mock_kernel[0].get_iopub_msg()

        msg1b = mock_kernel[0].get_iopub_msg()
        msg2b = mock_kernel[0].get_iopub_msg()
        msg3b = mock_kernel[0].get_iopub_msg()
        msg4b = mock_kernel[0].get_iopub_msg()

        # Process first state change message
        assert monitor.kernel_status == 'idle'
        assert monitor.can_store_activity_record is False
        monitor.handle_message(msg1a)
        assert monitor.kernel_status == 'busy'

        # Process input message
        monitor.handle_message(msg2a)
        assert len(monitor.current_cell.code) > 0
        assert len(monitor.cell_data) == 0
        assert monitor.can_store_activity_record is False

        # Process output message
        monitor.handle_message(msg3a)
        assert len(monitor.current_cell.result) > 0
        assert len(monitor.cell_data) == 0
        assert monitor.can_store_activity_record is False

        # Process final state change message
        monitor.handle_message(msg4a)
        assert monitor.kernel_status == 'idle'
        assert monitor.can_store_activity_record is True
        assert len(monitor.cell_data) == 1

        # Process first state change message
        assert monitor.kernel_status == 'idle'
        monitor.handle_message(msg1b)
        assert monitor.can_store_activity_record is False
        assert monitor.kernel_status == 'busy'

        # Process input message
        monitor.handle_message(msg2b)
        assert len(monitor.current_cell.code) > 0
        assert len(monitor.cell_data) == 1
        assert monitor.can_store_activity_record is False

        # Process output message
        monitor.handle_message(msg3b)
        assert len(monitor.current_cell.result) > 0
        assert len(monitor.cell_data) == 1
        assert monitor.can_store_activity_record is False

        # Process final state change message
        monitor.handle_message(msg4b)
        assert monitor.kernel_status == 'idle'
        assert monitor.can_store_activity_record is True
        assert len(monitor.cell_data) == 2

        # Store the record manually for this test
        monitor.store_record(metadata)
        assert monitor.can_store_activity_record is False
        assert len(monitor.cell_data) == 0

        # Check lab book repo state
        status = mock_labbook[2].git.status()
        assert len(status["untracked"]) == 0
        assert len(status["staged"]) == 0
        assert len(status["unstaged"]) == 0

        # Check activity entry
        log = mock_labbook[2].git.log()
        assert len(log) == 4
        assert 'code/Test.ipynb' in log[0]['message']

        a_store = ActivityStore(mock_labbook[2])
        record = a_store.get_activity_record(log[0]['commit'])
        assert record.type == ActivityType.CODE
        assert record.show is True
        assert record.importance == 0
        assert not record.tags
        assert record.message == 'Executed cell in notebook code/Test.ipynb'
        assert len(record.detail_objects) == 5
        assert record.detail_objects[0].show is True
        assert record.detail_objects[0].type.value == ActivityDetailType.RESULT.value
        assert record.detail_objects[0].importance == 155
        assert record.detail_objects[1].show is True
        assert record.detail_objects[1].type.value == ActivityDetailType.RESULT.value
        assert record.detail_objects[1].importance == 154
        assert record.detail_objects[2].show is False
        assert record.detail_objects[2].type.value == ActivityDetailType.CODE.value
        assert record.detail_objects[2].importance == 255
        assert record.detail_objects[3].show is False
        assert record.detail_objects[3].type.value == ActivityDetailType.CODE_EXECUTED.value
        assert record.detail_objects[3].importance == 255
        assert record.detail_objects[4].show is False
        assert record.detail_objects[4].type.value == ActivityDetailType.CODE_EXECUTED.value
        assert record.detail_objects[4].importance == 254
