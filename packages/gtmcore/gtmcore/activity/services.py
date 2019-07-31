from gtmcore.container.container import ContainerOperations
from gtmcore.labbook import LabBook
from typing import Optional
import time
import redis
from docker.errors import NotFound

from gtmcore.logging import LMLogger
from gtmcore.configuration import get_docker_client
from gtmcore.inventory.inventory import InventoryManager
from gtmcore.environment import ComponentManager
from gtmcore.gitlib.git import GitAuthor
from gtmcore.activity.monitors import DevEnvMonitorManager

from gtmcore.dispatcher import Dispatcher, JobKey
from gtmcore.dispatcher.jobs import run_dev_env_monitor
from gtmcore.container.utils import infer_docker_image_name


logger = LMLogger.get_logger()


# NOTE: Redis is used to track all Activity Monitoring processes in database 1. Keys:
#
# dev_env_monitor:<user>:<owner>:<labbook name>:<dev env name> -> Hash
#       container_name: <name of the lab book container>
#       labbook_root: <absolute path to the lab book root>
#       process_id: <id for the background task>
#        ... custom fields for the specific dev env monitor class
#
# dev_env_monitor:<user>:<owner>:<labbook name>:<dev env name>:activity_monitor:<UUID> -> Hash
#       dev_env_monitor: <dev_env_monitor key>
#       process_id: <id for the background task>
#        ... custom fields for the specific activity monitor class

# TODO DC: This is currently tuned to the organization of the Jupyter monitor, and should be made more generic,
# see issue #453
def start_labbook_monitor(labbook: LabBook, username: str, dev_tool: str,
                          url: str, database: int = 1,
                          author: Optional[GitAuthor] = None) -> None:
    """Method to start Development Environment Monitors for a given Lab Book if available

    Args:
        labbook(LabBook): A populated LabBook instance to start monitoring
        username(str): The username of the logged in user
        dev_tool(str): The name of the development tool to monitor
        url(str): URL (from LabManager) at which this dev tool can be reached.
        database(int): The redis database ID to use for key storage. Default should be 1
        author(GitAuthor): A GitAuthor instance for the current logged in user starting the monitor

    Returns:
        None
    """
    # Connect to redis
    redis_conn = redis.Redis(db=database)

    # Get all dev env monitors currently running
    dev_env_monitors = redis_conn.keys("dev_env_monitor:*")

    # Clean up after Lab Books that have "closed" by checking if the container is running
    docker_client = get_docker_client()
    for key in dev_env_monitors:
        if "activity_monitor" in key.decode():
            # Ignore all associated activity monitors, as they'll get cleaned up with the dev env monitor
            continue

        container_name = redis_conn.hget(key, 'container_name')
        try:
            docker_client.containers.get(container_name.decode())
        except NotFound:
            # Container isn't running, clean up
            logger.warn("Shutting down zombie Activity Monitoring for {}.".format(key.decode()))
            stop_dev_env_monitors(key.decode(), redis_conn, labbook.name)

    # Check if Dev Env is supported and then start Dev Env Monitor
    dev_env_mgr = DevEnvMonitorManager(database=database)

    if dev_env_mgr.is_available(dev_tool):
        # Add record to redis for Dev Env Monitor
        owner = InventoryManager().query_owner(labbook)
        dev_env_monitor_key = "dev_env_monitor:{}:{}:{}:{}".format(username,
                                                                   owner,
                                                                   labbook.name,
                                                                   dev_tool)

        if redis_conn.exists(dev_env_monitor_key):
            # Assume already set up properly (it wasn't cleaned up above)
            logger.info(f'Found existing entry for {dev_env_monitor_key}, skipping setup')
            return

        owner = InventoryManager().query_owner(labbook)
        redis_conn.hset(dev_env_monitor_key, "container_name", infer_docker_image_name(labbook.name,
                                                                                       owner,
                                                                                       username))
        redis_conn.hset(dev_env_monitor_key, "labbook_root", labbook.root_dir)
        redis_conn.hset(dev_env_monitor_key, "url", url)

        # Set author information so activity records can be committed on behalf of the user
        if author:
            redis_conn.hset(dev_env_monitor_key, "author_name", author.name)
            redis_conn.hset(dev_env_monitor_key, "author_email", author.email)

        # Schedule dev env
        d = Dispatcher()
        kwargs = {'dev_env_name': dev_tool,
                  'key': dev_env_monitor_key}
        job_key = d.schedule_task(run_dev_env_monitor, kwargs=kwargs, repeat=None, interval=3)
        redis_conn.hset(dev_env_monitor_key, "process_id", job_key.key_str)

        logger.info("Started `{}` dev env monitor for lab book `{}`".format(dev_tool, labbook.name))
    else:
        raise ValueError(f"{dev_tool} Developer Tool does not support monitoring")


# This one function could be tightened up to ensure that everything managed by a dev moniotor is cleaned up: containers, redis, etc.
# Part of #453
def stop_dev_env_monitors(dev_env_key: str, redis_conn: redis.Redis, labbook_name: str) -> None:
    """Method to stop a dev env monitor and all related activity monitors

    Args:
        dev_env_key(str): Key in redis containing the dev env monitor info
        redis_conn(redis.Redis): The redis instance to the state db
        labbook_name(str): The name of the related lab book - used only for logging / user messaging purposes

    Returns:

    """
    # Unschedule dev env monitor
    logger.info(f"Stopping dev env monitor {dev_env_key}")
    d = Dispatcher()
    process_id = redis_conn.hget(dev_env_key, "process_id")
    if process_id:
        logger.info("Dev Tool process id to stop: `{}` ".format(process_id))
        d.unschedule_task(JobKey(process_id.decode()))

        _, dev_env_name = dev_env_key.rsplit(":", 1)
        logger.info("Stopped dev tool monitor `{}` for lab book `{}`. PID {}".format(dev_env_name, labbook_name,
                                                                                     process_id))
        # Remove dev env monitor key
        redis_conn.delete(dev_env_key)

        # Make sure the monitor is unscheduled so it doesn't start activity monitors again
        time.sleep(2)
    else:
        logger.info("Shutting down container with no Dev Tool monitoring processes to stop.")

    # Get all related activity monitor keys
    activity_monitor_keys = redis_conn.keys("{}:activity_monitor*".format(dev_env_key))

    logger.info(f"Signaling {activity_monitor_keys} for shutdown.")
    # Signal all activity monitors to exit
    for am in activity_monitor_keys:
        # Set run flag in redis
        redis_conn.hset(am.decode(), "run", "False")
        logger.info("Signaled activity monitor for lab book `{}` to stop".format(labbook_name))


def stop_labbook_monitor(labbook: LabBook, username: str, database: int = 1) -> None:
    """Method to stop a Development Environment Monitors for a given Lab Book

    Args:
        labbook(LabBook): A populated LabBook instance to start monitoring
        username(str): Username of the logged in user
        database(int): The redis database ID to use for key storage. Default should be 1

    Returns:
        None

    """
    logger.info(f"Stopping labbook monitors for {labbook.name}")
    # Connect to redis
    redis_conn = redis.Redis(db=database)

    # Get Dev envs in the lab book
    cm = ComponentManager(labbook)
    base_data = cm.base_fields

    for dt in base_data['development_tools']:
        owner = InventoryManager().query_owner(labbook)
        dev_env_monitor_key = "dev_env_monitor:{}:{}:{}:{}".format(username,
                                                                   owner,
                                                                   labbook.name,
                                                                   dt)

        stop_dev_env_monitors(dev_env_monitor_key, redis_conn, labbook.name)
