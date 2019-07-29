import redis
import time
import argparse
import os
from typing import Optional, List, Dict
from threading import Lock, Thread
from multiprocessing import Process
from rq import Connection, Queue, Worker

from gtmcore.logging import LMLogger
from gtmcore.configuration import Configuration

logger = LMLogger.get_logger()

QUEUE_DEFAULT = 'gigantum-default-queue'
QUEUE_BUILD = 'gigantum-build-queue'
QUEUE_PUBLISH = 'gigantum-publish-queue'


class WorkerService:
    """Represents the background job management "microservice". Handles
    allotment of queues and workers, as well as optional bursting of
    workers and jobs. """

    def __init__(self, config_path: Optional[str] = None, db: Optional[int] = None):
        self._config = Configuration(config_file=config_path).config
        self._redis_db = db
        self._worker_process_lock = Lock()
        self._worker_process_list: List[Process] = []
        self._is_monitoring = True
        self._queue_names = (QUEUE_BUILD, QUEUE_PUBLISH, QUEUE_DEFAULT)

    def _default_conn(self):
        return redis.Redis(db=13)

    def start(self):
        """Start all of the workers for all of the queues. """
        # Attempt to load configured count of workers per queue, otherwise use
        # the given defaults here.
        q_default = QueueLoader(QUEUE_DEFAULT, self._config, 7)
        q_build = QueueLoader(QUEUE_BUILD, self._config, 1)
        q_publish = QueueLoader(QUEUE_PUBLISH, self._config, 4)
        for queue in (q_default, q_build, q_publish):
            for _ in range(queue.nworkers):
                self._start_worker(queue.name)

    def query(self):

        response = {'isBursting': self.is_bursting}
        response.update({
            qname: {
                'idleWorkers': len(self.get_idle_workers(qname)),
                'totalWorkers': len(self.get_all_workers(qname))
            }
            for qname in self._queue_names
        })
        return response

    @property
    def is_bursting(self) -> bool:
        """Return True if there are currently bursted processes running, implying
        that the overall dispatching system may be temporarily overloaded. """
        default_worker_cnt = QueueLoader(QUEUE_DEFAULT, self._config, 7).nworkers
        return len(self.get_all_workers(QUEUE_DEFAULT)) > default_worker_cnt

    @property
    def worker_processes(self) -> List[Process]:
        """List of all workers as regular processes."""
        return self._worker_process_list

    def _append_worker_process(self, process: Process) -> None:
        with self._worker_process_lock:
            self._worker_process_list.append(process)

    def get_idle_workers(self, queue_name: str) -> List[Worker]:
        """ Returns only the IDLE workers for a given queue. Implicitly all these
        workers are non-bursted (persistent). """
        return [w for w in self.get_all_workers(queue_name) if w.get_state() == 'idle']

    def get_all_workers(self, queue_name: str) -> List[Worker]:
        """ Returns a list of all the given workers for the given queue. """
        return Worker.all(queue=Queue(queue_name, connection=self._default_conn()))

    def monitor_burstable_queue(self) -> None:
        """Blocking routine to monitor the default queue and burst new workers if needed.
        Note that this routine may never exit. """

        burstable_queue = 'gigantum-default-queue'
        while self._is_monitoring:
            # Removed completed workers
            with self._worker_process_lock:
                new_list = [w for w in self._worker_process_list if w.is_alive()]
                self._worker_process_list = new_list

            idle_workers = self.get_idle_workers(burstable_queue)
            if len(idle_workers) == 0:
                for _ in range(5):
                    # When required to burst, burst 5 processes. We need to hard code
                    # this due to a minor bug in RQ (apparently). Using `Queue.get_jobs`
                    # does not properly work, so we cannot count the number of queued
                    # jobs.
                    logger.warning(f"Bursting new worker for {burstable_queue}")
                    worker_proc = self._start_worker(burstable_queue, burst=True)
                    self._append_worker_process(worker_proc)
            time.sleep(5)

    def _start_worker(self, queue_name: str, burst: bool = False) -> Process:
        """Launch a new RQ worker process to consume jobs for the given queue name.

        Args:
            queue_name: Name of the redis queue this worker will listen on
            burst: When true, this worker will terminate as soon as the queue is empty.

        Returns:
            Reference to the worker process itself.
        """
        p = Process(target=start_rq_worker, args=(queue_name, burst))
        p.start()
        return p

    def stop(self):
        """Wait for all worker processes to complete. Note this may never exit. """
        for p in self.worker_processes:
            p.join()


def start_rq_worker(queue_name: str, burst: bool = False) -> None:
    """Start an RQ worker for the given queue. """
    try:
        with Connection(connection=redis.Redis(db=13)):
            q = Queue(name=queue_name)
            logger.info(f"Starting {'BURSTED ' if burst else ''}"
                        f"RQ worker for in {queue_name}")
            if burst:
                Worker(q).work(burst=True)
            else:
                # This is to bypass a problem when the user closes their laptop
                # (All the workers time out and die). This should prevent that up until a week.
                wk_in_secs = 60 * 60 * 24 * 7
                Worker(q, default_result_ttl=wk_in_secs, default_worker_ttl=wk_in_secs).work()
    except Exception as e:
        logger.exception("Worker in pid {} failed with exception {}".format(os.getpid(), e))
        raise


class QueueLoader:
    def __init__(self, name: str, config: Dict, nworkers: int):
        self.name = name
        self.nworkers = self._get_worker_count(config, default=nworkers)
        logger.info(f"Initialized queue {self.name} with {self.nworkers} workers.")

    def _get_worker_count(self, config: Dict, default: int) -> int:
        try:
            return config['dispatcher'][self.name.replace('-', '_')]
        except KeyError:
            logger.warning(f"Missing config for Dispatcher queue {self.name}; "
                           f"Defaulting to {default} worker(s).")
            return default


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Launch RQ workers per config file')
    parser.add_argument('--config', type=str, default=None, help='Path to config file')
    parser.add_argument('--db', type=int, default=None, help='Redis DB to use')

    try:
        args = parser.parse_args()
    except Exception as e:
        logger.exception(e)
        raise

    try:
        worker_service = WorkerService(args.config)
        worker_service.start()
        worker_service.monitor_burstable_queue()
        worker_service.stop()
    except Exception as e:
        logger.exception(e)



