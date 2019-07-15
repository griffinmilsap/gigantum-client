from typing import Optional, List
import os

from gtmcore.dispatcher.dispatcher import Dispatcher, JobKey, JobStatus
from gtmcore.dataset.manifest import Manifest
from gtmcore.logging import LMLogger

logger = LMLogger.get_logger()

MAX_JOB_BYTES = 1e9


class BackgroundHashJob:
    """Class to help track background hashing jobs"""
    def __init__(self, dispatcher: Dispatcher, file_list: list, total_bytes: int) -> None:
        self.dispatcher = dispatcher
        self.file_list = file_list
        self.total_bytes = total_bytes
        self.failure_count = 0
        self.job_key: Optional[JobKey] = None

        self._job_status: Optional[JobStatus] = None

    @property
    def is_running(self) -> bool:
        """Boolean indicating if the job has been scheduled and is running"""
        if not self._job_status:
            return False

        if self._job_status.status in ["started", "queued"]:
            return True
        else:
            return False

    @property
    def is_failed(self) -> bool:
        """Boolean indicating if the job has failed"""
        if not self._job_status:
            return False

        if self._job_status.status == "failed":
            return True
        else:
            return False

    @property
    def is_complete(self) -> bool:
        """Boolean indicating if the job has completed"""
        if not self._job_status:
            return False

        if self._job_status.status == "finished":
            return True
        else:
            return False

    def refresh_status(self) -> bool:
        """Method to query the dispatcher for the job's state. If the job failed, self.failure_count will increment.
        The method also returns self.is_complete after the status update is complete

        Returns:
            bool
        """
        if self.job_key:
            if self._job_status:
                prior_job_state = self._job_status.status
            else:
                prior_job_state = "NO_PRIOR_STATE"

            self._job_status = self.dispatcher.query_task(self.job_key)

            if self._job_status:
                if prior_job_state != self._job_status.status:
                    if self.is_failed:
                        self.failure_count += 1

        return self.is_complete

    def get_hash_result(self) -> List[Optional[str]]:
        """Method to get the hash result for all files in self.file_list

        Returns:
            list
        """
        if not self._job_status:
            raise ValueError("No job status available. Run `refresh_status` before checking for result")
        if not self.is_complete:
            raise ValueError("Job must successfully complete before checking for result")

        hash_result = self._job_status.meta['hash_result'].split(',')
        return [None if v == 'None' else v for v in hash_result]

    def get_fast_hash_result(self) -> List[Optional[str]]:
        """Method to get the fast hash result for all files in self.file_list

        Returns:

        """
        if not self._job_status:
            raise ValueError("No job status available. Run `refresh_status` before checking for result")
        if not self.is_complete:
            raise ValueError("Job must successfully complete before checking for result")

        fast_hash_result = self._job_status.meta['fast_hash_result'].split(',')
        return [None if v == 'None' else v for v in fast_hash_result]


def generate_bg_hash_job_list(filenames: List[str],
                              manifest: Manifest,
                              dispatcher_obj: Dispatcher) -> List[BackgroundHashJob]:
    """Method to generate batches of files to be hashed, ensuring files aren't added to a batch once it is
    larger than MAX_JOB_BYTES

    Args:
        filenames: list of files to be hashed
        manifest: the Manifest instance
        dispatcher_obj: the Dispatcher instance

    Returns:
        list
    """
    num_cores = manifest.get_num_hashing_cpus()
    file_lists: List[List] = [list() for _ in range(num_cores)]
    size_sums = [0 for _ in range(num_cores)]
    revision_dir = manifest.current_revision_dir

    for filename in filenames:
        index = size_sums.index(min(size_sums))
        file_lists[index].append(filename)
        size_sums[index] += os.path.getsize(os.path.join(revision_dir, filename))
        if all(fs > MAX_JOB_BYTES for fs in size_sums):
            # 1GB of data to hash already in every job. Add another.
            file_lists.append(list())
            size_sums.append(0)

    # Prune Jobs back if there are lots of cores but not lots of work
    file_lists = [x for x in file_lists if x != []]
    size_sums = [x for x in size_sums if x != 0]

    # Prep hashing jobs
    return [BackgroundHashJob(dispatcher_obj, fl, ss) for ss, fl in zip(size_sums, file_lists)]
