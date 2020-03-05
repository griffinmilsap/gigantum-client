import uuid
import re
import os
import time
from typing import Optional

import redis
import requests

from gtmcore.logging import LMLogger
from gtmcore.environment import ComponentManager
from gtmcore.container import ContainerOperations
from gtmcore.labbook import LabBook
from gtmcore.exceptions import GigantumException

logger = LMLogger.get_logger()

DEFAULT_JUPYTER_PORT = 8888
PYTHON_ENV_CMD = "PYTHONPATH=/mnt/share:$PYTHONPATH"


def start_jupyter(project_container: ContainerOperations, check_reachable: bool = True,
                  proxy_prefix: Optional[str] = None) -> str:
    """ Main entrypoint to launching Jupyter. Note, the caller must
        determine for themselves the host and port.

    Returns:
        Path to jupyter (e.g., "/lab?token=xyz")
    """
    if project_container.query_container() != 'running':
        raise GigantumException(
            f"{str(project_container.labbook)} container is not running. Start it before launch a dev tool.")

    # Get IP of container on Docker Bridge Network
    lb_ip_addr = project_container.query_container_ip()
    if not lb_ip_addr:
        raise GigantumException("Can't obtain IP address for Jupyter container")

    jupyter_ps = project_container.ps_search('jupyter lab', reps=1)

    if len(jupyter_ps) == 1:
        logger.info(f'Found existing Jupyter instance for {str(project_container.labbook)}.')

        # Get token
        redis_conn = redis.Redis(db=1)
        token = redis_conn.get(f"{project_container.image_tag}-jupyter-token")
        if token:
            token_str = f"token={token.decode()}"
        else:
            token_str = ""
        suffix = f'{proxy_prefix or ""}/lab/tree/code?{token_str}'

        if check_reachable:
            check_jupyter_reachable(lb_ip_addr, DEFAULT_JUPYTER_PORT, f'{proxy_prefix or ""}')

        return suffix
    elif len(jupyter_ps) == 0:
        new_token = uuid.uuid4().hex.replace('-', '')
        if proxy_prefix and proxy_prefix[0] != '/':
            proxy_prefix = f'/{proxy_prefix}'
        _start_jupyter_process(project_container, new_token, proxy_prefix)
        suffix = f'{proxy_prefix or ""}/lab/tree/code?token={new_token}'

        if check_reachable:
            check_jupyter_reachable(lb_ip_addr, DEFAULT_JUPYTER_PORT, f'{proxy_prefix or ""}')

        return suffix
    else:
        # If "ps aux" for jupyterlab returns multiple hits - this should never happen.
        for n, l in enumerate(jupyter_ps):
            logger.error(f'Multiple JupyerLab instances - ({n+1} of {len(jupyter_ps)}) - {l}')
        raise ValueError(f'Multiple Jupyter Lab instances detected in project env. You should restart the container.')


def _shim_skip_python2_savehook(labbook: LabBook) -> bool:
    """Return True if the LabBook uses a Python 2 base image.
    If the base is Python 2, we cannot use the save hook. There is no upstream fix coming. """
    cm = ComponentManager(labbook)
    return 'python2' in cm.base_fields['id'].lower().replace(' ', '')


def _start_jupyter_process(project_container: ContainerOperations, token: str,
                           proxy_prefix: Optional[str] = None) -> None:
    if not project_container.labbook:
        raise ValueError('ContainerOperations object must include a LabBook (Project)')
    labbook = project_container.labbook
    use_savehook = os.path.exists('/mnt/share/jupyterhooks') \
                   and not _shim_skip_python2_savehook(labbook)

    project_container.configure_dev_tool('jupyterlab')

    cmd = (f'echo "{project_container.username},{labbook.owner},{labbook.name},{token}" > /home/giguser/jupyter_token'
           " && cd /mnt/labbook"
           f" && {PYTHON_ENV_CMD} jupyter lab --port={DEFAULT_JUPYTER_PORT} --ip=0.0.0.0 "
           f"--NotebookApp.token='{token}' --no-browser "
           '--ConnectionFileMixin.ip=0.0.0.0 ' +
           ('--FileContentsManager.post_save_hook="jupyterhooks.post_save_hook" '
            if use_savehook else "") +
           (f'--NotebookApp.base_url="{proxy_prefix}" '
            if proxy_prefix else ''))

    project_container.exec_command(cmd, user='giguser')

    if not project_container.ps_search('jupyter lab'):
        raise ValueError('Jupyter Lab failed to start after 10 seconds')

    # Store token in redis for later activity monitoring
    # (activity data is stored in db1)
    redis_conn = redis.Redis(db=1)
    redis_conn.set(f"{project_container.image_tag}-jupyter-token", token)


def check_jupyter_reachable(ip_address: str, port: int, prefix: str):
    test_url = f'http://{ip_address}:{port}{prefix}/api'

    for n in range(30):
        logger.debug(f"Attempt {n + 1}: Testing if Jupyter is up at {test_url}...")
        try:
            r = requests.get(test_url, timeout=0.5)
            if r.status_code != 200:
                time.sleep(0.5)
            else:
                if "version" in r.json():
                    logger.info(f'Found Jupyter up at {test_url} after {n/2.0} seconds')
                    break
                else:
                    time.sleep(0.5)
        except requests.exceptions.ConnectionError:
            # Assume API isn't up at all yet, so no connection can be made
            time.sleep(0.5)
    else:
        raise GigantumException(f'Could not reach Jupyter at {test_url} after timeout')
