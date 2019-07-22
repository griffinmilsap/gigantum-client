import redis_lock
from contextlib import contextmanager
from redis import StrictRedis

from gtmcore.configuration import Configuration
from gtmcore.logging import LMLogger


logger = LMLogger.get_logger()


class FileWriteLock:
    def __init__(self, filename: str, config_instance: Configuration) -> None:

        self.config = config_instance.config['lock']
        self.filename = filename

        # Redis instance for the LabBook lock
        self._lock_redis_client = StrictRedis(host=self.config['redis']['host'],
                                              port=self.config['redis']['port'],
                                              db=self.config['redis']['db'])

    @contextmanager
    def lock(self):
        """A context manager for locking files while writing in a multi-process configuration"""
        lock: redis_lock.Lock = None
        try:
            lock_key = f'filesystem_lock|{self.filename}'

            # Get a lock object
            lock = redis_lock.Lock(self._lock_redis_client, lock_key,
                                   expire=self.config['expire'],
                                   auto_renewal=self.config['auto_renewal'],
                                   strict=self.config['redis']['strict'])

            lock_kwargs = {'timeout': 30}
            if lock.acquire(**lock_kwargs):
                # Do the work
                yield
            else:
                raise IOError(f"Could not acquire file system lock within 30 seconds.")

        except Exception as e:
            logger.error(e)
            raise
        finally:
            # Release the Lock
            if lock:
                try:
                    lock.release()
                except redis_lock.NotAcquired as e:
                    # if you didn't get the lock and an error occurs, you probably won't be able to release, so log.
                    logger.error(e)
