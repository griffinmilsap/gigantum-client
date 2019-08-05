import os
from glob import glob

import time
from confhttpproxy import ProxyRouter
from typing import Optional, Tuple, List

import redis
from docker.errors import NotFound

from gtmcore.configuration import get_docker_client
from gtmcore.container.utils import ps_search
from gtmcore.labbook import LabBook
from gtmcore.container.container import ContainerOperations
from gtmcore.logging import LMLogger
from gtmcore.exceptions import GigantumException

logger = LMLogger.get_logger()
CURRENT_MITMPROXY_TAG = 'eab6f480'


class MITMProxyOperations(object):
    logfile_dir = 'mitmproxy'

    @classmethod
    def configure_mitmroute(cls, labbook: LabBook, router: ProxyRouter, username: str,
                            _retry: Optional[bool] = False) -> Tuple[str, str]:
        """Ensure mitm is configured and proxied for labbook

        Args:
            labbook: the specific target running a dev tool
            router: The link to the configurable-proxy-router wrapper
            username: username of the logged in user
            _retry: (internal use only) is this a recursive call after clean-up?

        Returns:
            str that contains the mitm proxy endpoint as http://{ip}:{port}
        """
        labbook_container_name = ContainerOperations.labbook_image_name(labbook, username)
        # Note that the use of rserver is not intrinsically meaningful - we could make this more generic
        # if mitmproxy supports multiple dev tools
        proxy_target = f'rserver/{labbook_container_name}/'
        mitm_key = cls.get_mitm_redis_key(labbook_container_name)

        redis_conn = redis.Redis(db=1)

        devtool_ip = ContainerOperations.get_labbook_ip(labbook, username)
        devtool_endpoint = f"http://{devtool_ip}:8787"

        for monitored_labbook_name in cls.get_running_proxies():
            # We clean up all running MITM proxy containers
            if (monitored_labbook_name != labbook_container_name) and \
                    (cls.get_devtool_endpoint(monitored_labbook_name) == devtool_endpoint):
                # Some other MITM proxy is pointing at our dev tool
                cls.stop_mitm_proxy(monitored_labbook_name)

        if not redis_conn.exists(mitm_key):
            # start mitm proxy if it's not configured yet - we'll delete a stopped container first in this call
            mitm_endpoint = cls.start_mitm_proxy(devtool_endpoint, labbook_container_name)

            # add route
            rt_prefix, _ = router.add(mitm_endpoint, proxy_target)
            # Warning: RStudio will break if there is a trailing slash!
            suffix = f'/{rt_prefix}'
        elif _retry:
            # This should never happen - but it's better than the chance of infinite recursion
            raise ValueError(f'Unable to cleanly stop mitmproxy_proxy for {labbook_container_name}. Please try manually.')
        else:
            # Are we pointing to the correct dev tool endpoint?
            configured_devtool_endpoint = cls.get_devtool_endpoint(labbook_container_name)
            if devtool_endpoint != configured_devtool_endpoint:
                logger.warning(f'Existing RStudio mitmproxy_proxy for stale endpoint {configured_devtool_endpoint}, removing')
                cls.stop_mitm_proxy(labbook_container_name)
                return cls.configure_mitmroute(labbook, router, username, _retry=True)

            # Is the MITM endpoint configured in Redis?
            retval = cls.get_mitmendpoint(labbook_container_name)
            if retval is None:
                logger.warning('Existing RStudio mitmproxy_proxy is partially configured, removing')
                cls.stop_mitm_proxy(labbook_container_name)
                return cls.configure_mitmroute(labbook, router, username, _retry=True)
            else:
                mitm_endpoint = retval

            # existing route to MITM or not?
            matched_routes = router.get_matching_routes(mitm_endpoint, proxy_target)

            if len(matched_routes) == 1:
                suffix = matched_routes[0]
            elif len(matched_routes) == 0:
                logger.warning('Creating missing route for existing RStudio mitmproxy_proxy')
                rt_prefix, _ = router.add(mitm_endpoint, proxy_target)
                # Warning: RStudio will break if there is a trailing slash!
                suffix = f'/{rt_prefix}'
            else:
                raise ValueError(f"Multiple RStudio proxy instances for {str(labbook)}. Please restart the Project "
                                 "or manually delete stale containers.")

        # The endpoint plus proxy target constitute the full URL for an MITM-reverse-proxied RStudio
        return f"{mitm_endpoint}/{proxy_target}", suffix

    @classmethod
    def get_mitmendpoint(cls, labbook_container_name: str) -> Optional[str]:
        """Determine in there is a proxy installed for this endpoint

        Args:
            labbook_container_name: the specific target running a dev tool

        Returns:
            str that contains the proxy endpoint as http://{ip}:{port}
        """
        hkey = cls.get_mitm_redis_key(labbook_container_name)
        redis_conn = redis.Redis(db=1)
        retval = redis_conn.hget(hkey, "endpoint")
        if retval:
            return retval.decode()
        else:
            return None

    @classmethod
    def get_mitmcontainerid(cls, labbook_container_name: str) -> Optional[str]:
        """Return the container associated with the mitm proxy.

        Args:
            labbook_container_name: the specific target running a dev tool

        Returns:
        str that contains the containerid
        """
        hkey = cls.get_mitm_redis_key(labbook_container_name)
        redis_conn = redis.Redis(db=1)
        retval = redis_conn.hget(hkey, "container_id")
        if retval:
            return retval.decode()
        else:
            return None

    @classmethod
    def get_mitmlogfile_path(cls, labbook_container_name: str) -> Optional[str]:
        """Return the logfile path associated with the mitm proxy.

        Args:
            labbook_container_name: the specific target running a dev tool

        Returns:
        str that contains the logfile path
        """
        hkey = cls.get_mitm_redis_key(labbook_container_name)
        redis_conn = redis.Redis(db=1)
        retval = redis_conn.hget(hkey, "logfile_path")
        if retval:
            return retval.decode()
        else:
            return None

    @classmethod
    def get_devtool_endpoint(cls, labbook_container_name: str) -> Optional[str]:
        """Return the dev tool container endpoint for the currently running mitm proxy.

        Args:
            labbook_container_name: the specific target running a dev tool

        Returns:
        str that contains the dev tool container endpoint
        """
        hkey = cls.get_mitm_redis_key(labbook_container_name)
        redis_conn = redis.Redis(db=1)
        retval = redis_conn.hget(hkey, "devtool_endpoint")
        if retval:
            return retval.decode()
        else:
            return None

    @classmethod
    def get_mitm_redis_key(cls, labbook_container_name: str):
        """Centralized convention for the hash key for an MITM proxy

        Args:
            labbook_container_name: the specific target running a dev tool

        Returns:
            str that contains the mitm hash key
        """
        return f"mitm:{labbook_container_name}"

    @classmethod
    def start_mitm_proxy(cls, devtool_endpoint: str, target_key: str) -> str:
        """Launch a proxy cointainer between client and labbook.

        Args:
            devtool_endpoint: the specific target running a dev tool
            target_key: a unique key for this instance (related to the monitored Project container - e.g., RStudio)

        Returns:
            str that contains the proxy endpoint as http://{ip}:{port}
        """
        hkey = cls.get_mitm_redis_key(target_key)

        # setup the environment - note that UID is obtained inside the container based on labmanager_share_vol
        # (mounted at /mnt/share)
        logfile_path = f'/mnt/share/{cls.logfile_dir}/{target_key}.rserver.dump'

        env_var = [f"LBENDPOINT={devtool_endpoint}", f"LOGFILE_NAME={logfile_path}"]
        nametag = f"gmitmproxy.{target_key}"
        volumes_dict = {
            'labmanager_share_vol': {'bind': '/mnt/share', 'mode': 'rw'}
        }

        docker_client = get_docker_client()

        try:
            zombie_container = docker_client.containers.get(nametag)
            # Should have already cleaned up running containers before calling
            # So we could assume this is stopped, but this shouldn't happen often
            # and it doesn't hurt to be paranoid
            logger.warning(f"Removing stopped container {nametag}, will create anew")
            zombie_container.remove(force=True)
        except NotFound:
            # good!
            pass

        container = docker_client.containers.run("gigantum/mitmproxy_proxy:" + CURRENT_MITMPROXY_TAG, detach=True,
                                                 init=True, name=nametag, volumes=volumes_dict,
                                                 environment=env_var)

        # We hammer repeatedly for 5 seconds (this should be very fast since it's a small, simple container)
        for _ in range(10):
            time.sleep(.5)
            # Hope that our container is actually up and reload
            container.reload()
            mitm_ip = container.attrs['NetworkSettings']['Networks']['bridge']['IPAddress']
            if mitm_ip:
                break

        if not mitm_ip:
            raise GigantumException("Unable to get mitmproxy_proxy IP address.")

        # This is the port for NGINX
        mitm_endpoint = f'http://{mitm_ip}:8079'

        # register the proxy in KV store
        redis_conn = redis.Redis(db=1)
        redis_conn.hset(hkey, "endpoint", mitm_endpoint)
        redis_conn.hset(hkey, "container_id", container.id)
        redis_conn.hset(hkey, "logfile_path", logfile_path)
        redis_conn.hset(hkey, "devtool_endpoint", devtool_endpoint)

        # make sure proxy is up.
        for timeout in range(10):
            time.sleep(1)
            if ps_search(container, 'nginx'):
                logger.info(f"Proxy to rserver started within {timeout + 1} seconds")
                break
        else:
            raise ValueError('mitmproxy failed to start after 10 seconds')

        return mitm_endpoint

    @classmethod
    def get_running_proxies(cls) -> List[str]:
        """Return a list of the running gmitmproxy

            Returns: List of strs with image names for proxied dev tool containers.
        """
        client = get_docker_client()
        clist = client.containers.list(filters={'ancestor': 'gigantum/mitmproxy_proxy:' + CURRENT_MITMPROXY_TAG})
        retlist = []
        for cont in clist:
            # container name is gmitmproxy.<mitm key> - currently the monitored container image name
            _, container_key = cont.name.split('.')
            retlist.append(container_key)
        return retlist

    @classmethod
    def clean_logfiles(cls):
        active_logfiles = {cls.get_mitmlogfile_path(proxied_name) for proxied_name in cls.get_running_proxies()}
        existing_logfiles = set(glob(f'/mnt/share/{cls.logfile_dir}/*.rserver.dump'))

        for logfile in (existing_logfiles - active_logfiles):
            # yes logfile, no mitm proxy -> exited kernel delete file
            logger.info(f"Detected defunct RStudio-Server log. Deleting log {logfile}")
            os.remove(logfile)

        # Note that we aren't stopping MITM proxies that lack a logfile nor are we returning those logfiles
        # That shouldn't happen, but we log here just in case
        if active_logfiles - existing_logfiles:
            logger.error('Found running MITM (RStudio) proxies with no log file present')

        return existing_logfiles.intersection(active_logfiles)

    @classmethod
    def stop_mitm_proxy(cls, labbook_container_name: str) -> Optional[str]:
        """Stop the MITM proxy. Destroy container. Delete volume.

        Args:
            labbook_container_name: the specific target running a dev tool

        Returns:
            ip address of the mitm_proxy for removing the route (if configured) else None
        """
        container_id = MITMProxyOperations.get_mitmcontainerid(labbook_container_name)

        # stop the mitm container
        docker_client = get_docker_client()
        mitm_container = docker_client.containers.get(container_id)
        mitm_container.stop()
        mitm_container.remove()

        mitm_endpoint = cls.get_mitmendpoint(labbook_container_name)

        # unregister the proxy in KV store
        redis_conn = redis.Redis(db=1)

        hkey = cls.get_mitm_redis_key(labbook_container_name)
        redis_conn.delete(hkey)

        return mitm_endpoint
