import time
import subprocess
from typing import List
from gtmcore.logging import LMLogger

logger = LMLogger.get_logger()


def call_subprocess(cmd_tokens: List[str], cwd: str, check: bool = True,
                    shell: bool = False) -> str:
    """Execute a subprocess call and properly benchmark and log

    Args:
        cmd_tokens: List of command tokens, e.g., ['ls', '-la']
        cwd: Current working directory
        check: Raise exception if command fails
        shell: Run as shell command (not recommended)

    Returns:
        Decoded stdout of called process after completing

    Raises:
        subprocess.CalledProcessError
    """
    logger.debug(f"Executing `{' '.join(cmd_tokens)}` in {cwd}")
    start_time = time.time()
    try:
        r = subprocess.run(cmd_tokens, cwd=cwd, stderr=subprocess.PIPE, stdout=subprocess.PIPE,
                           check=check, shell=shell)
        finish_time = time.time()
        elapsed_time = finish_time - start_time
        logger.debug(f"Finished command `{' '.join(cmd_tokens)}` in {elapsed_time:.2f}s")
        if elapsed_time > 1.0:
            logger.warning(f"Successful command `{' '.join(cmd_tokens)}` took {elapsed_time:.2f}s")
        return (r.stdout or b"").decode()
    except subprocess.CalledProcessError as x:
        fail_time = time.time() - start_time
        logger.error(f"Command failed `{' '.join(cmd_tokens)}` after {fail_time:.2f}s: "
                     f"stderr={x.stderr}, stdout={x.stdout}")
        raise
