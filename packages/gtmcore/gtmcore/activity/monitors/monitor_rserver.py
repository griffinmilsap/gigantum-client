import traceback
import time

import json
import pandas
import redis
from docker.errors import NotFound
import mitmproxy.io as mitmio
from mitmproxy.exceptions import FlowReadException
from typing import (Dict, List, Optional, BinaryIO)

from gtmcore.activity import ActivityType
from gtmcore.activity.monitors.activity import ActivityMonitor
from gtmcore.activity.monitors.devenv import DevEnvMonitor
from gtmcore.activity.monitors.rserver_exchange import RserverExchange
from gtmcore.activity.processors.core import GenericFileChangeProcessor, ActivityShowBasicProcessor, \
    ActivityDetailLimitProcessor
from gtmcore.activity.processors.processor import ExecutionData
from gtmcore.activity.processors.rserver import (RStudioServerCodeProcessor,
                                                 RStudioServerPlaintextProcessor,
                                                 RStudioServerImageExtractorProcessor)
from gtmcore.activity.services import stop_dev_env_monitors
from gtmcore.configuration import get_docker_client
from gtmcore.dispatcher import Dispatcher, jobs
from gtmcore.logging import LMLogger
from gtmcore.mitmproxy.mitmproxy import MITMProxyOperations

logger = LMLogger.get_logger()


def format_output(output: Dict):
    """Produce suitable JSON output for storing an R data frame in an Activity Record

    Args:
        output: the representation of a dataframe returned by
    """
    om = output.get('output_metadata')
    if om:
        omc = om.get('classes')
        # We currently don't deal with any complex outputs apart from data.frame
        # We'll log other metadata types below
        if omc and 'data.frame' in omc:
            try:
                column_names = [x['label'][0] for x in output['output_val']['columns']]
                df = pandas.DataFrame.from_dict(output['output_val']['data'])
                df.columns = column_names
                if df.shape[0] <= 50:
                    return {'data': {'text/plain': str(df)},
                            'tags': 'data.frame'}
                else:
                    output_text = str(df.head(20)) + \
                                  f"\n.....,..and {df.shape[0] - 20} more rows"
                    return {'data': {'text/plain': output_text},
                            'tags': 'data.frame'}

            # This bare except is left in-place because there are number of ways the above could fail,
            # but it's hard to imagine any big surprises, and this default behavior is completely reasonable.
            except:
                return {'data': {'text/plain': json.dumps(output['output_val'])},
                        'tags': 'data.frame'}
        else:
            logger.error(f"RStudio output with unknown metadata: {om}")
            return None
    else:
        logger.error(f"No metadata for chunk_output: {output}")
        return None


class RServerMonitor(DevEnvMonitor):
    """Class to monitor RStudio-Server for the need to start Activity Monitor Instances"""

    @staticmethod
    def get_dev_env_name() -> List[str]:
        """Method to return a list of names of the development environments that this class interfaces with.
        Should be the value used in the `name` attribute of the Dev Env Environment Component"""
        return ["rstudio"]

    def get_activity_monitor_lb_names(self, dev_env_monitor_key: str, redis_conn: redis.Redis) -> List[str]:
        """Return a list of the current activity monitors

        Currently only used in testing.

            Returns: List of strs with name of proxied labbook.
        """
        # Get list of active Activity Monitor Instances from redis
        # dev_env_monitor_key should specify rstudio at this point, and there should only be one key
        activity_monitor_keys = redis_conn.keys('{}:activity_monitor:*'.format(dev_env_monitor_key))
        activity_monitor_keys = [x.decode() for x in activity_monitor_keys]
        retlist = []
        try:
            for am in activity_monitor_keys:
                logfid = redis_conn.hget(am, "logfile_id")
                if logfid:
                    retlist.append(logfid.decode())
        # decode throws error on unset values.  not sure how to check RB
        except Exception as e:
            logger.error(f'Unhandled exception in get_activity_monitor_lb_names: {e}')
            raise
        return retlist

    def run(self, dev_env_monitor_key: str, database: int = 1) -> None:
        """Method called in a periodically scheduled async worker that should check the dev env and manage Activity
        Monitor Instances as needed

        Args:
            dev_env_monitor_key: The unique string used as the key in redis to track this DevEnvMonitor instance
            database: The redis database number for dev env monitors to use
        """
        redis_conn = redis.Redis(db=database)
        activity_monitor_key = f'{dev_env_monitor_key}:activity_monitor'

        retval = redis_conn.hget(dev_env_monitor_key, 'container_name')
        if retval:
            labbook_container_name = retval.decode()
        else:
            # This shouldn't happen, but just in case
            logger.error(f'No container name for DevTool Monitor {dev_env_monitor_key}, stopping')
            # This should clean up everything this monitor is managing
            # labbook name is just for logging purposes, so we supply 'unknown'
            stop_dev_env_monitors(dev_env_monitor_key, redis_conn, 'unknown')
            return

        # For now, we directly query docker, this could be cleaned up in #453
        client = get_docker_client()
        try:
            dev_env_container_status = client.containers.get(labbook_container_name).status
        except NotFound:
            dev_env_container_status = 'not found'

        # Clean up and return labbook container names for running proxies
        running_proxy_lb_names = MITMProxyOperations.get_running_proxies()

        # As part of #453, we should re-start the proxy if the dev tool is still running
        if labbook_container_name not in running_proxy_lb_names:
            # MITM proxy isn't running anymore.
            logger.info(f"Detected exited RStudio proxy {labbook_container_name}. Stopping monitoring for {activity_monitor_key}")
            logger.info(f"Running proxies: {running_proxy_lb_names}")
            # This should clean up everything it's managing
            stop_dev_env_monitors(dev_env_monitor_key, redis_conn, labbook_container_name)
        elif dev_env_container_status != "running":
            # RStudio container isn't running anymore. Clean up by setting run flag to `False` so worker exits
            logger.info(f"Detected exited RStudio Project {labbook_container_name}. Stopping monitoring for {activity_monitor_key}")
            logger.info(f"Running proxies: {running_proxy_lb_names}")
            # This should clean up everything it's managing
            stop_dev_env_monitors(dev_env_monitor_key, redis_conn, labbook_container_name)
            # I don't believe we yet have a way to fit MITM proxy cleanup into the abstract dev env monitor machinery
            # Could be addressed in #453
            MITMProxyOperations.stop_mitm_proxy(labbook_container_name)
        else:
            am_running = redis_conn.hget(activity_monitor_key, 'run')
            if not am_running or am_running.decode() == 'False':
                # Get author info
                # RB this is not populated until a labbook is started why running?
                author_name = redis_conn.hget(dev_env_monitor_key, "author_name").decode()
                author_email = redis_conn.hget(dev_env_monitor_key, "author_email").decode()
                # Start new Activity Monitor
                _, user, owner, labbook_name, dev_env_name = dev_env_monitor_key.split(':')

                args = {"module_name": "gtmcore.activity.monitors.monitor_rserver",
                        "class_name": "RStudioServerMonitor",
                        "user": user,
                        "owner": owner,
                        "labbook_name": labbook_name,
                        "monitor_key": activity_monitor_key,
                        "author_name": author_name,
                        "author_email": author_email,
                        "session_metadata": None}

                d = Dispatcher()
                process_id = d.dispatch_task(jobs.start_and_run_activity_monitor, kwargs=args, persist=True)
                logger.info(f"Started RStudio Server Notebook Activity Monitor: Process {process_id}")

                # Update redis
                redis_conn.hset(activity_monitor_key, "process_id", process_id.key_str)
                redis_conn.hset(activity_monitor_key, "run", "True")
                redis_conn.hset(activity_monitor_key, "logfile_path",
                                MITMProxyOperations.get_mitmlogfile_path(labbook_container_name))


class RStudioServerMonitor(ActivityMonitor):
    """Class to monitor an rstudio server for activity to be processed.

    currently, this class conflates two separable concerns:
      1. Setting up activity processing for ExecutionData entries into ActivityRecords
      2. Actually parsing activity and creating the ExecutionData entries
    """

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

        # R's chunks are about equivalent to cells in Jupyter, these will be indexed by chunk_id
        # Console / script output will be indexed with chunk_id 'console'
        self.active_execution = ExecutionData()
        # ExecutionData that's ready to be stored
        # For now, we save an ActivityRecord whenever we change active_doc_id, so doc_id doesn't need to be
        # stored per record here
        self.completed_executions: List[ExecutionData] = []

        # There are at least four ways that code is communicated back and forth between the front and back end
        # For now, we use the rpc execution paths to switch to a new context
        # This means we need to keep context if we saw multiple chunks in one request
        self.remaining_chunks: List[Dict] = []

        # This will attempt to mirror what the RStudio backend knows for each doc_id
        self.doc_properties: Dict[str, Dict] = {'console': {'name': 'console'}}
        # Keep track of where we're executing - if we switch documents, we will store what we've got in
        # completed_executions to an ActivityRecord
        self.active_doc_id = 'console'
        # Extracted from write_console_input (which is used for commands from any source).
        # Known values include the empty string for direct console execution, or chunk_id when available.
        self.active_console: str = ''
        # The names of yet-unseen images that we saw in a get_events call
        self.expected_images: List[str] = []

    def register_processors(self) -> None:
        """Method to register processors

        Returns:
            None
        """
        self.add_processor(RStudioServerCodeProcessor())
        self.add_processor(GenericFileChangeProcessor())
        self.add_processor(RStudioServerPlaintextProcessor())
        self.add_processor(RStudioServerImageExtractorProcessor())
        self.add_processor(ActivityDetailLimitProcessor())
        self.add_processor(ActivityShowBasicProcessor())

    def start(self, metadata: Dict[str, str], database: int = 1) -> None:
        """Method called in a periodically scheduled async worker that should check the dev env and manage Activity
        Monitor Instances as needed

        Args:
            metadata(dict): A dictionary of data to start the activity monitor
            database(int): The database ID to use

        Returns:
            None
        """
        # Get connection to the DB
        redis_conn = redis.Redis(db=database)

        logfile_path = redis_conn.hget(self.monitor_key, "logfile_path")

        mitmlog = open(logfile_path, "rb")
        if not mitmlog:
            logger.info(f"Failed to open RStudio log {logfile_path}")
            return

        try:
            while True:
                still_running = redis_conn.hget(self.monitor_key, "run")
                # Check if you should exit
                # sometimes this runs after key has been deleted.  None is shutdown too.
                if not still_running or still_running.decode() == "False":
                    logger.info(f"Received Activity Monitor Shutdown Message for {self.monitor_key}")
                    redis_conn.delete(self.monitor_key)
                    break

                # Read activity and update aggregated "cell" data
                self.process_activity(mitmlog)

                # Check for new records every second
                time.sleep(1)

        except Exception as e:
            # This is rather verbose, but without the stack trace, it's almost completely useless as
            # the Exception could have come from anywhere!
            logger.error(f"Fatal error in RStudio Server Activity Monitor: {e}\n{traceback.format_exc()}")
            raise
        finally:
            # Delete the kernel monitor key so the dev env monitor will spin up a new process
            # You may lose some activity if this happens, but the next action will sweep up changes
            logger.info(f"Shutting down RStudio monitor {self.monitor_key}")
            redis_conn.delete(self.monitor_key)
            # At this point, there is no chance we'll get anything else out of unmonitored files!
            MITMProxyOperations.clean_logfiles()

    def store_record(self) -> None:
        """Store R input/output/code to ActivityRecord / git commit

        store_record() should be called after moving any data in self.active_execution to
        self.completed_executions. You should also check self.expected_images before calling this.
        """
        if self.expected_images:
            logger.error(f'Expected images: {", ".join(self.expected_images)}')
            self.expected_images = []

        if self.completed_executions:
            t_start = time.time()

            # Process collected data and create an activity record
            codepath = self.safe_doc_name()

            activity_record = self.process(ActivityType.CODE, list(reversed(self.completed_executions)),
                                           {'path': codepath})

            # Commit changes to the related Notebook file
            commit = self.commit_labbook()

            try:
                # Create note record
                activity_commit = self.store_activity_record(commit, activity_record)
                logger.info(f"Created auto-generated activity record {activity_commit} in {time.time() - t_start} seconds")
            except Exception as e:
                logger.error(f'Encountered fatal error generating activity record: {e}')
            finally:
                # This is critical - otherwise if we have an error, we'll keep spawning new activity monitors that die!
                self.completed_executions = []

    def _parse_backend_events(self, json_record: Dict) -> None:
        """Extract code and data from the record.

        When context switches between console <-> notebook, we store a record for
        the previous execution and start a new record.

        Args:
            json_record: dictionary parsed from mitmlog
        """
        result = json_record.get('result')
        # No result ignore
        if not result:
            return

        # parse the entries in this message
        for edata, etype in [(entry.get('data'), entry.get('type')) for entry in result]:
            # All observed executions include this command to indicate it was entered to the R prompt
            if etype == 'console_write_input':
                # This is the empty string for direct entry, or otherwise indicates the source of the code
                console_id = edata['console']
                if console_id != self.active_console:
                    # Maybe we're onto a new, expected chunk...
                    self._new_execution(new_console=console_id)

            elif etype == 'chunk_output':
                outputs = edata.get('chunk_outputs')
                if outputs:
                    for oput in outputs:
                        result = format_output(oput)
                        if result:
                            self.active_execution.result.append(result)

                oput = edata.get('chunk_output')
                if oput:
                    output_val = oput['output_val']
                    if type(output_val) is str and output_val.endswith('.png'):
                        # This should look like: chunk_output/46E01830e058b169/C065EDF7/cln6e9n2q4150/000003.png
                        # The actual http fetch will add an initial `/`
                        self.expected_images.append('/' + oput['output_val'])
                    else:
                        result = format_output(oput)
                        if result:
                            self.active_execution.result.append(result)




            # this happens in both notebooks and console
            elif etype == 'console_output':
                self.active_execution.result.append({'data': {'text/plain': edata['text']}})

            # handle report of figure -> expected
            elif etype == 'plots_state_changed' and edata['filename'] != 'empty.png':
                # This filename is now available at '/graphics/{filename}'
                self.expected_images.append('/graphics/' + edata['filename'])

            # For future reference: we can detect when chunk is completed (etype of chunk_output_finished),
            #  or when console execution is finished (etype console_write prompt, edata of '> ') if needed

    def _is_error(self, result: Dict) -> bool:
        """Check if there's an error in the message"""
        for entry in result:
            if entry['type'] == 'console_error':
                return True
        else:
            return False

    def safe_doc_name(self, doc_id: Optional[str] = None) -> str:
        """"Try to get a name from doc_properties safely

        If it's missing, we create a default name for the doc_id. Hopefully one that gets fixed later!
        """
        if doc_id is None:
            doc_id = self.active_doc_id
        properties = self.doc_properties.get(doc_id, {'name': f'ID: {doc_id}'})
        return properties['name']

    def _new_execution(self, exchange: Optional[RserverExchange] = None, new_console: Optional[str] = None) -> None:
        """Set up a new execution and cycle / store active_exectution and store an ActivityRecord as needed

        exchange:
            New entry from MITM - leave None to pop off the next chunk from remaining_chunks
        new_console:
            console specified from write_console_input

        Updates / resets the following attributes:
         - expected_images
         - active_console (which is either the chunk_id or '')
         - active_doc_id
         - remaining_chunks
        """
        # Whatever was going on, we're gonna drop it and complete the active execution
        for image_name in self.expected_images:
            logger.error(f"Expected {image_name} for execution from {self.safe_doc_name()}")
        self.expected_images = []

        if exchange:
            if self.remaining_chunks:
                logger.error('Saw chunks via /rpc/execute_notebook_chunks that were not apparently executed')
                # This will get overwritten below

            # Extract info about the new context
            if exchange.path == '/rpc/console_input':
                new_doc = 'console'
                # console_input is simple - we just get the code
                new_code = exchange.request['params'][0].rstrip()
                # RStudio uses an empty string for commands that actually originate from the console
                self.active_console = ''
                self.remaining_chunks = []
            elif exchange.path == '/rpc/execute_notebook_chunks':
                # This is complicated - we get a big dict
                params = exchange.request['params'][0]
                new_doc = params['doc_id']
                chunks = params['units']
                new_code = chunks[0]['code'].rstrip()
                # We'll check that our `write_console_input` events match this
                self.active_console = chunks[0]['chunk_id']
                self.remaining_chunks = chunks[1:]
            else:
                logger.error(f'Unknown path for new execution {exchange.path}')
                return

        elif self.remaining_chunks:
            if new_console is None:
                raise TypeError('Must provide either exchange or new_console argument to _new_execution()')
            next_chunk = self.remaining_chunks[0]
            if next_chunk['chunk_id'] == new_console:
                # It's a match
                self.active_console = new_console
                self.remaining_chunks = self.remaining_chunks[1:]
                new_code = next_chunk['code'].rstrip()
                # This has always been observed to be the same, but doesn't hurt - the information is there
                new_doc = next_chunk['doc_id']
            else:
                # We ignore this issue for now because it should never happen
                # The next full-on RPC call (execute_notebook_chunks or console_input) will clear this out
                logger.error(f'Found unexpected console input from {new_console}')
                return

        else:
            logger.error('Trying to shift to new chunk execution, but no expected chunks remain')
            return

        if not self.active_execution.is_empty():
            self.completed_executions.append(self.active_execution)
            self.active_execution = ExecutionData()
        self.active_execution.code.append({'code': new_code})

        # if we've switched documents, store a record
        if new_doc != self.active_doc_id:
            self.store_record()
            self.active_doc_id = new_doc

    def _handle_image(self, exchange: RserverExchange) -> None:
        """Append the image to the current chunk

        Also report an error if chunk_id doesn't match. We assume that there is ALWAYS an available `ExecutionData`
        instance in self.active_execution
        """
        if exchange.path.startswith('/chunk_output/'):
            # This is from a document chunk execution, and looks like:
            # /chunk_output/46E01830e058b169/C065EDF7/cln6e9n2q4150/000003.png
            try:
                self.expected_images.remove(exchange.path)
            except ValueError:
                logger.error(f'found unexpected graphic during chunk execution')

            segments = exchange.path.split('/')
            chunk_id = segments[4]
            if chunk_id != self.active_console:
                # Note that we don't let graphics override the document context... ultimately, this shouldn't happen anyway
                # But we'll store what we can
                doc_id = segments[3]
                doc_name = self.safe_doc_name(doc_id)
                logger.error(f'RStudioServerMonitor found graphic from rogue execution context for {doc_name}.')

            self.active_execution.result.append({'data': {'image/png': exchange.response}})
        elif exchange.path.startswith("/graphics/"):
            # This is from a script/console execution and looks like this (pretty sure a UUID):
            # /graphics/ce4c938e-15f3-4da8-b193-0e3bdae0cf7d.png
            try:
                self.expected_images.remove(exchange.path)
            except ValueError:
                logger.error(f'found unexpected graphic during console execution')

            if self.active_doc_id != 'console':  # active_console would equivalently be ''
                # Again, we don't let graphics override the document context...
                logger.error(f'found graphic from console during chunk execution')
            self.active_execution.result.append({'data': {'image/png': exchange.response}})
        else:
            logger.error(f'Got image from unknown path {exchange.path}')

    def _update_doc_names(self, exchange: RserverExchange) -> None:
        """Parse the JSON response information from RStudio - keeping track of code, output, and metadata

        Note that there are two different document types! "Notebooks" and an older "Document" type"""
        fname = None
        doc_id = None

        # For a new file, the first time we get a user-facing id is when the front end gives a tempName
        if exchange.path == '/rpc/modify_document_properties':
            doc_id, properties = exchange.request['params']
            if 'tempName' in properties:
                fname = properties['tempName']
        # Later, a filename may be assigned by the front end via a save
        # Haven't yet traced through what happens on save-as or loading a file instead of new -> save
        elif exchange.path == '/rpc/save_document_diff':
            params = exchange.request['params']
            fname = params[1]
            if fname:
                doc_id = params[0]
        # Or, we can open an existing file
        elif exchange.path == '/rpc/open_document':
            result = exchange.response['result']
            doc_id = result['id']
            fname = result['path']

        if doc_id and fname:
            self.doc_properties.setdefault(doc_id, {})['name'] = fname.lstrip('/mnt/labbook/')

    def process_activity(self, mitmlog: BinaryIO):
        """Collect tail of the activity log and turn into an activity record.

        Args:
            mitmlog(file): open file object

        Returns:
            ar(): activity record
        """
        # get an fstream generator object
        fstream = iter(mitmio.FlowReader(mitmlog).stream())

        while True:
            try:
                mitm_message = next(fstream)
            except StopIteration:
                break
            except FlowReadException as e:
                # TODO issue #938
                logger.info("MITM Flow file corrupted: {}. Exiting.".format(e))
                break

            try:
                rserver_exchange = RserverExchange(mitm_message.get_state())
            except json.JSONDecodeError as je:
                logger.info(f"Ignoring JSON Decoder Error for Rstudio message {je}.")
                continue

            # process images
            if rserver_exchange.response_type == 'image/png':
                # I guess non-zipped images should not occur?
                if rserver_exchange.response_headers.get('Content-Encoding') == 'gzip':
                    self._handle_image(rserver_exchange)
                else:
                    logger.error(f"RSERVER Found image/png that was not gzip encoded.")

            elif rserver_exchange.response_type == 'application/json':
                # code or output event
                if rserver_exchange.path == "/events/get_events":
                    # There are some special case get_events calls at the beginning of a session.
                    # We ignore those.
                    if rserver_exchange.request['params'][0] != -1:
                        # get text/code fields out of dictionary
                        self._parse_backend_events(rserver_exchange.response)
                elif rserver_exchange.path in ['/rpc/console_input', '/rpc/execute_notebook_chunks']:
                    self._new_execution(rserver_exchange)
                else:
                    self._update_doc_names(rserver_exchange)

        # This logic isn't air-tight, but should at worst simply split what should've been in one execution
        #  across two ActivityRecords.
        # We do know that we've exhausted the MITM log file, so we got out in front of the `get_event` calls, etc.
        if not (self.expected_images or self.remaining_chunks):
            if not self.active_execution.is_empty():
                self.completed_executions.append(self.active_execution)
                self.active_execution = ExecutionData()
            self.store_record()
