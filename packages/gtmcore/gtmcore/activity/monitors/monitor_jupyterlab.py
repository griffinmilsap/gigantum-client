import os
import queue
import json
from typing import (Any, Dict, List, Optional)
import time

import jupyter_client
import redis
import requests

from gtmcore.activity.processors.processor import ExecutionData
from gtmcore.container import container_for_context
from gtmcore.activity.monitors.devenv import DevEnvMonitor
from gtmcore.activity.monitors.activity import ActivityMonitor
from gtmcore.activity.processors.jupyterlab import JupyterLabCodeProcessor, \
    JupyterLabPlaintextProcessor, JupyterLabImageExtractorProcessor, JupyterLabCellVisibilityProcessor
from gtmcore.activity.processors.core import ActivityShowBasicProcessor, GenericFileChangeProcessor, \
    ActivityDetailLimitProcessor, ActivityDetailProgressProcessor
from gtmcore.activity import ActivityType
from gtmcore.dispatcher import Dispatcher, jobs
from gtmcore.logging import LMLogger

logger = LMLogger.get_logger()


class JupyterLabMonitor(DevEnvMonitor):
    """Class to monitor JupyterLab for the need to start Activity Monitor Instances"""

    @staticmethod
    def get_dev_env_name() -> List[str]:
        """Method to return a list of names of the development environments that this class interfaces with.
        Should be the value used in the `name` attribute of the Dev Env Environment Component"""
        return ["jupyterlab"]

    @staticmethod
    def get_sessions(key: str, redis_conn: redis.Redis) -> Dict[str, Any]:
        """Method to get and reformat session info from JupyterLab

        Args:
            key(str): The unique string used as the key in redis to track this DevEnvMonitor instance
            redis_conn(redis.Redis): A redis client

        Returns:
            dict
        """

        _, username, owner, labbook_name, _ = key.split(':')
        project_info = container_for_context(username)
        lb_key = project_info.default_image_tag(owner, labbook_name)
        token_bytes = redis_conn.get(f"{lb_key}-jupyter-token")
        if token_bytes:
            token = token_bytes.decode()
        else:
            logger.warning(f"No token in cache when checking Jupyter sessions for {username}/{owner}/{labbook_name}")
            token = ""
        url = redis_conn.hget(key, "url").decode()

        # Get List of active sessions
        path = f'{url}/api/sessions?token={token}'
        r = requests.get(path)
        if r.status_code != 200:
            raise IOError(f"Failed to get session listing from JupyterLab {path}")
        sessions = r.json()

        data = {}
        for session in sessions:
            data[session['kernel']['id']] = {"kernel_id": session['kernel']['id'],
                                             "kernel_name": session['kernel']['name'],
                                             "kernel_type": session['type'],
                                             "path": session['path']}
        return data

    def run(self, dev_env_monitor_key: str, database: int = 1) -> None:
        """Method called in a periodically scheduled async worker that should check the dev env and manage Activity
        Monitor Instances as needed Args:
            dev_env_monitor_key(str): The unique string used as the dev_env_monitor_key in redis to track this DevEnvMonitor instance
        """
        # Check if the runtime directory exists, and if not create it
        if not os.path.exists(os.environ['JUPYTER_RUNTIME_DIR']):
            os.makedirs(os.environ['JUPYTER_RUNTIME_DIR'])
            logger.info("Created Jupyter shared runtime dir: {}".format(os.environ['JUPYTER_RUNTIME_DIR']))

        # Get list of active Activity Monitor Instances from redis
        redis_conn = redis.Redis(db=database)
        activity_monitors = redis_conn.keys('{}:activity_monitor:*'.format(dev_env_monitor_key))
        activity_monitors = [x.decode('utf-8') for x in activity_monitors]

        # Get author info
        author_name = redis_conn.hget(dev_env_monitor_key, "author_name").decode()
        author_email = redis_conn.hget(dev_env_monitor_key, "author_email").decode()

        # Get session info from Jupyter API
        sessions = self.get_sessions(dev_env_monitor_key, redis_conn)

        # Check for exited kernels
        for am in activity_monitors:
            kernel_id = redis_conn.hget(am, "kernel_id").decode()
            if kernel_id not in sessions:
                if redis_conn.hget(am, 'run').decode() != 'False':
                    logger.info("Detected exited JupyterLab kernel. Stopping monitoring for kernel id {}".format(kernel_id))
                    # Kernel isn't running anymore. Clean up by setting run flag to `False` so worker exits
                    redis_conn.hset(am, 'run', 'False')

        # Check for new kernels
        for s in sessions:
            if sessions[s]['kernel_type'] == 'notebook':
                # Monitor a notebook
                activity_monitor_key = '{}:activity_monitor:{}'.format(dev_env_monitor_key, sessions[s]['kernel_id'])
                if activity_monitor_key not in activity_monitors:
                    logger.info("Detected new JupyterLab kernel. Starting monitoring for kernel id {}".format(sessions[s]['kernel_id']))

                    # Start new Activity Monitor
                    _, user, owner, labbook_name, dev_env_name = dev_env_monitor_key.split(':')

                    args = {"module_name": "gtmcore.activity.monitors.monitor_jupyterlab",
                            "class_name": "JupyterLabNotebookMonitor",
                            "user": user,
                            "owner": owner,
                            "labbook_name": labbook_name,
                            "monitor_key": activity_monitor_key,
                            "author_name": author_name,
                            "author_email": author_email,
                            "session_metadata": sessions[s]}
                    d = Dispatcher()
                    process_id = d.dispatch_task(jobs.start_and_run_activity_monitor, kwargs=args, persist=True)
                    logger.info("Started Jupyter Notebook Activity Monitor: {}".format(process_id))

                    # Update redis
                    redis_conn.hset(activity_monitor_key, "dev_env_monitor", dev_env_monitor_key)
                    redis_conn.hset(activity_monitor_key, "process_id", process_id.key_str)
                    redis_conn.hset(activity_monitor_key, "path", sessions[s]["path"])
                    redis_conn.hset(activity_monitor_key, "kernel_type", sessions[s]["kernel_type"])

                    redis_conn.hset(activity_monitor_key, "kernel_name", sessions[s]["kernel_name"])
                    redis_conn.hset(activity_monitor_key, "kernel_id", sessions[s]["kernel_id"])
                    redis_conn.hset(activity_monitor_key, "run", str(True))


class JupyterLabNotebookMonitor(ActivityMonitor):
    """Class to monitor a notebook kernel for activity to be processed."""

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
        # Call super constructor
        ActivityMonitor.__init__(self, user, owner, labbook_name, monitor_key, config_file,
                                 author_name=author_name, author_email=author_email)

        # For now, register processors by default
        self.register_processors()

        # Tracking variables during message processing
        self.kernel_status = 'idle'
        self.current_cell = ExecutionData()
        self.cell_data: List[ExecutionData] = list()
        self.execution_count = 0

    def register_processors(self) -> None:
        """Method to register processors

        Returns:
            None
        """
        self.add_processor(JupyterLabCodeProcessor())
        self.add_processor(GenericFileChangeProcessor())
        self.add_processor(JupyterLabPlaintextProcessor())
        self.add_processor(JupyterLabImageExtractorProcessor())
        self.add_processor(JupyterLabCellVisibilityProcessor())
        self.add_processor(ActivityDetailProgressProcessor())
        self.add_processor(ActivityDetailLimitProcessor())
        self.add_processor(ActivityShowBasicProcessor())

    # We use an underspecified type for msg, as the impedance mismatch between Jupyter IOpub "traitlets" and mypy is
    # too much! cf. https://github.com/jupyter/jupyter_client/blob/master/jupyter_client/client.py
    def handle_message(self, msg: Dict[str, Any]):
        """Method to handle processing an IOPub Message from a JupyterLab kernel

        Args:
            msg(dict): An IOPub message


        Returns:
            None
        """
        # Initialize can_process to False. This variable is used to indicate if the cell data should be processed into
        # an ActivityRecord and saved
        if msg['msg_type'] == 'status':
            # If status was busy and transitions to idle store cell since execution has completed
            if self.kernel_status == 'busy' and msg['content']['execution_state'] == 'idle':
                self.set_busy_state(False)

                if self.current_cell.cell_error is False and self.current_cell.is_empty() is False:
                    # Current cell did not error and has content
                    # Add current cell to collection of cells ready to process
                    self.cell_data.append(self.current_cell)

                # Reset current_cell attribute for next execution
                self.current_cell = ExecutionData()

                # Indicate record COULD be processed if timeout occurs
                self.can_store_activity_record = True

            elif self.kernel_status == 'idle' and msg['content']['execution_state'] == 'busy':
                # Starting to process new cell execution
                self.set_busy_state(True)
                self.can_store_activity_record = False

            # Update status
            self.kernel_status = msg['content']['execution_state']

        elif msg['msg_type'] == 'execute_input':
            # A message containing the input to kernel has been received
            self.current_cell.code.append({'code': msg['content']['code']})
            self.execution_count = int(msg['content']['execution_count'])
            self.current_cell.tags.append(f"ex:{msg['content']['execution_count']}")

        elif msg['msg_type'] == 'execute_result':
            # A message containing the output of a cell execution has been received
            if self.execution_count != msg['content']['execution_count']:
                logger.error("Execution count mismatch detected {},{}".format(self.execution_count,
                                                                              msg['content']['execution_count']))

            self.current_cell.result.append({'data': msg['content']['data'], 'metadata': msg['content']['metadata']})

        elif msg['msg_type'] == 'stream':
            # A message containing plaintext output of a cell execution has been received
            self.current_cell.result.append({'data': {"text/plain": msg['content']['text']},
                                             'metadata': {'source': 'stream'}})

        elif msg['msg_type'] == 'display_data':
            # A message containing rich output of a cell execution has been received
            self.current_cell.result.append({'data': msg['content']['data'], 'metadata': {'source': 'display_data'}})

        elif msg['msg_type'] == 'error':
            # An error occurred, so don't save this cell by resetting the current cell attribute.
            self.current_cell.cell_error = True

        else:
            logger.info("Received and ignored IOPUB Message of type {}".format(msg['msg_type']))

    def store_record(self, metadata: Dict[str, str]) -> None:
        """Method to create and store an activity record

        Args:
            metadata(dict): A dictionary of data to start the activity monitor

        Returns:
            None
        """
        if len(self.cell_data) > 0:
            t_start = time.time()

            # Process collected data and create an activity record
            activity_record = self.process(ActivityType.CODE, list(reversed(self.cell_data)), {"path": metadata["path"]})

            # Commit changes to the related Notebook file
            commit = self.commit_labbook()

            # Create note record
            activity_record = self.store_activity_record(commit, activity_record)
            activity_commit = activity_record.commit

            logger.info(f"Created auto-generated activity record {activity_commit} in {time.time() - t_start} seconds")

        # Reset for next execution
        self.can_store_activity_record = False
        self.cell_data = list()
        self.current_cell = ExecutionData()

    def start(self, metadata: Dict[str, str], database: int = 1) -> None:
        """Method called in a periodically scheduled async worker that should check the dev env and manage Activity
        Monitor Instances as needed

        Args:
            metadata(dict): A dictionary of data to start the activity monitor
            database(int): The database ID to use

        Returns:
            None
        """
        # Connect to the kernel
        cf = jupyter_client.find_connection_file(metadata["kernel_id"], path=os.environ['JUPYTER_RUNTIME_DIR'])
        km = jupyter_client.BlockingKernelClient()

        with open(cf, 'rt') as cf_file:
            cf_data = json.load(cf_file)

        # Get IP address of lab book container on the bridge network
        container_ip = self.get_container_ip()

        if not container_ip:
            raise ValueError("Failed to find LabBook container IP address.")
        cf_data['ip'] = container_ip

        # Open ports if needed.
        ports = [int(cf_data['shell_port']),
                 int(cf_data['iopub_port']),
                 int(cf_data['stdin_port']),
                 int(cf_data['control_port']),
                 int(cf_data['hb_port'])]

        project_container = container_for_context(self.user, labbook=self.labbook)
        project_container.open_ports(ports)

        km.load_connection_info(cf_data)

        # Get connection to the DB
        redis_conn = redis.Redis(db=database)

        try:
            while True:
                try:
                    # Check for messages, waiting up to 1 second. This is the rate that records will be merged
                    msg = km.get_iopub_msg(timeout=1)
                    self.handle_message(msg)

                except queue.Empty:
                    # if queue is empty and the record is ready to store, save it!
                    if self.can_store_activity_record is True:
                        self.store_record(metadata)

                # Check if you should exit
                if redis_conn.hget(self.monitor_key, "run").decode() == "False":
                    logger.info("Received Activity Monitor Shutdown Message for {}".format(metadata["kernel_id"]))
                    break

        except Exception as err:
            logger.error("Error in JupyterLab Activity Monitor: {}".format(err))
        finally:
            # Delete the kernel monitor key so the dev env monitor will spin up a new process
            # You may lose some activity if this happens, but the next action will sweep up changes
            redis_conn.delete(self.monitor_key)
