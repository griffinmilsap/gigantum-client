import copy
import os
import time
from typing import Optional, List

from humanfriendly import format_size
from rq import get_current_job

from gtmcore.configuration import Configuration
from gtmcore.dataset import Manifest
from gtmcore.dataset.manifest.job import generate_bg_hash_job_list
from gtmcore.dispatcher import Dispatcher
from gtmcore.gitlib import GitAuthor, RepoLocation
from gtmcore.inventory.inventory import InventoryManager, InventoryException
from gtmcore.logging import LMLogger
from gtmcore.workflows import gitworkflows_utils
from gtmcore.workflows.gitlab import GitLabManager
from gtmcore.dataset.io.manager import IOManager
from gtmcore.dataset.io.job import BackgroundDownloadJob
from gtmcore.dataset.io import PushObject


def hash_dataset_files(logged_in_username: str, dataset_owner: str, dataset_name: str,
                       file_list: List, config_file: str = None) -> None:
    """

    Args:
        logged_in_username: username for the currently logged in user
        dataset_owner: Owner of the labbook if this dataset is linked
        dataset_name: Name of the labbook if this dataset is linked
        file_list: List of files to be hashed
        config_file: Optional config file to use

    Returns:
        None
    """
    logger = LMLogger.get_logger()

    p = os.getpid()
    try:
        logger.info(f"(Job {p}) Starting hash_dataset_files(logged_in_username={logged_in_username},"
                    f"dataset_owner={dataset_owner}, dataset_name={dataset_name}")

        ds = InventoryManager(config_file=config_file).load_dataset(logged_in_username, dataset_owner, dataset_name)
        manifest = Manifest(ds, logged_in_username)

        hash_result, fast_hash_result = manifest.hash_files(file_list)

        job = get_current_job()
        if job:
            job.meta['hash_result'] = ",".join(['None' if v is None else v for v in hash_result])
            job.meta['fast_hash_result'] = ",".join(['None' if v is None else v for v in fast_hash_result])
            job.save_meta()

    except Exception as err:
        logger.error(f"(Job {p}) Error in clean_dataset_file_cache job")
        logger.exception(err)
        raise


def complete_dataset_upload_transaction(logged_in_username: str, logged_in_email: str,
                                        dataset_owner: str, dataset_name: str, dispatcher,
                                        config_file: str = None) -> None:
    """Method to import a dataset from a zip file

    Args:
        logged_in_username: username for the currently logged in user
        logged_in_email: email for the currently logged in user
        dataset_owner: Owner of the labbook if this dataset is linked
        dataset_name: Name of the labbook if this dataset is linked
        dispatcher: Reference to the dispatcher CLASS
        config_file: config file (used for test mocking)

    Returns:
        None
    """
    logger = LMLogger.get_logger()
    dispatcher_obj = dispatcher()

    def update_feedback(msg: str, has_failures: Optional[bool] = None, failure_detail: Optional[str] = None,
                        percent_complete: Optional[float] = None):
        """Method to update the job's metadata and provide feedback to the UI"""
        current_job = get_current_job()
        if not current_job:
            return
        if has_failures:
            current_job.meta['has_failures'] = has_failures
        if failure_detail:
            current_job.meta['failure_detail'] = failure_detail
        if percent_complete:
            current_job.meta['percent_complete'] = percent_complete

        current_job.meta['feedback'] = msg
        current_job.save_meta()

    def schedule_bg_hash_job():
        """Method to check if a bg job should get scheduled and do so"""
        num_cores = manifest.get_num_hashing_cpus()
        if sum([x.is_running for x in job_list]) < num_cores:
            for j in job_list:
                if j.is_failed is True and j.failure_count < 3:
                    # Re-schedule failed job
                    job_kwargs['file_list'] = j.file_list
                    job_key = dispatcher_obj.dispatch_task(hash_dataset_files,
                                                           kwargs=job_kwargs,
                                                           metadata=job_metadata)
                    j.job_key = job_key
                    update_feedback(f"Restarted failed file hashing job. Re-processing"
                                    f" {format_size(j.total_bytes)}...")
                    logger.info(f"(Job {p}) Restarted file hash job for"
                                f" {logged_in_username}/{dataset_owner}/{dataset_name}")
                    break

                if j.is_complete is False and j.is_running is False:
                    # Schedule new job
                    job_kwargs['file_list'] = j.file_list
                    job_key = dispatcher_obj.dispatch_task(hash_dataset_files,
                                                           kwargs=job_kwargs,
                                                           metadata=job_metadata)
                    j.job_key = job_key
                    logger.info(f"(Job {p}) Scheduled file hash job for"
                                f" {logged_in_username}/{dataset_owner}/{dataset_name}")
                    break

    p = os.getpid()
    try:
        logger.info(f"(Job {p}) Starting complete_dataset_upload_transaction(logged_in_username={logged_in_username},"
                    f"dataset_owner={dataset_owner}, dataset_name={dataset_name}")

        author = GitAuthor(name=logged_in_username, email=logged_in_email)
        dispatcher_obj = Dispatcher()
        ds = InventoryManager(config_file=config_file).load_dataset(logged_in_username, dataset_owner, dataset_name,
                                                                    author=author)
        manifest = Manifest(ds, logged_in_username)

        with ds.lock():
            # Detect changes
            status = manifest.status()

            # Collect filenames that need to be hashed
            filenames = copy.deepcopy(status.modified)
            filenames.extend(status.created)

            # If there are new/updated files, spread work across cores while providing reasonable feedback
            if filenames:
                job_list = generate_bg_hash_job_list(filenames, manifest, dispatcher_obj)
                total_bytes = sum([x.total_bytes for x in job_list])

                job_kwargs = {
                    'logged_in_username': logged_in_username,
                    'dataset_owner': dataset_owner,
                    'dataset_name': dataset_name,
                    'file_list': list(),
                    'config_file': config_file,
                }
                job_metadata = {'dataset': f"{logged_in_username}|{dataset_owner}|{dataset_name}",
                                'method': 'hash_dataset_files'}

                update_feedback(f"Please wait while file contents are analyzed. "
                                f"Processing {format_size(total_bytes)}...", has_failures=False)
                logger.info(f"(Job {p}) Starting file hash processing for"
                            f" {logged_in_username}/{dataset_owner}/{dataset_name} with {len(job_list)} jobs")

                while True:
                    # Check if you need to schedule jobs and schedule up to 1 job per iteration
                    schedule_bg_hash_job()

                    # Refresh all job statuses and update status feedback
                    completed_job_status = [x.refresh_status() for x in job_list]
                    completed_bytes = sum([s.total_bytes for s, c in zip(job_list, completed_job_status) if c is True])
                    update_feedback(f"Please wait while file contents are analyzed. "
                                    f"{format_size(completed_bytes)} of {format_size(total_bytes)} complete...",
                                    percent_complete=(float(completed_bytes)/float(total_bytes)) * 100)

                    # Check if you are done
                    completed_or_failed = sum([(x.is_complete or (x.failure_count >= 3)) for x in job_list])
                    if completed_or_failed == len(job_list):
                        break

                    # Update once per second
                    time.sleep(1)

                # Manually complete update process for updated/created files
                failed_files = list()
                for job in job_list:
                    if job.is_complete:
                        for f, h, fh in zip(job.file_list, job.get_hash_result(), job.get_fast_hash_result()):
                            if not fh or not h:
                                failed_files.append(f)
                                continue

                            _, file_bytes, mtime = fh.split("||")
                            manifest._manifest_io.add_or_update(f, h, mtime, file_bytes)
                    else:
                        failed_files.extend(job.file_list)

                # Message for hard failures
                if failed_files:
                    detail_msg = f"The following files failed to hash. Try re-uploading the files again:\n"
                    detail_file_list = " \n".join(failed_files)
                    detail_msg = f"{detail_msg}{detail_file_list}"
                    update_feedback(f"An error occurred while processing some files. Check details and re-upload.",
                                    has_failures=True, failure_detail=detail_msg)

            if status.deleted:
                manifest.hasher.delete_fast_hashes(status.deleted)
                for relative_path in status.deleted:
                    manifest._manifest_io.remove(relative_path)

            manifest._manifest_io.persist()

            # Complete sweep operation
            manifest.sweep_all_changes(status=status, upload=True)

    except Exception as err:
        logger.error(f"(Job {p}) Error in clean_dataset_file_cache job")
        logger.exception(err)
        raise


def check_and_import_dataset(logged_in_username: str, dataset_owner: str, dataset_name: str, remote_url: str,
                             access_token: Optional[str] = None, id_token: Optional[str] = None,
                             config_file: Optional[str] = None) -> None:
    """Job to check if a dataset exists in the user's working directory, and if not import it. This is primarily used
    when importing, syncing, or switching branches on a project with linked datasets

    Args:
        logged_in_username: username for the currently logged in user
        dataset_owner: Owner of the labbook if this dataset is linked
        dataset_name: Name of the labbook if this dataset is linked
        remote_url: URL of the dataset to import if needed
        access_token: The current user's access token, needed to initialize git credentials in certain situations
        id_token: The current user's id token, needed to initialize git credentials in certain situations
        config_file: config file (used for test mocking)

    Returns:
        None
    """
    logger = LMLogger.get_logger()
    p = os.getpid()
    logger.info(f"(Job {p}) Starting check_and_import_dataset(logged_in_username={logged_in_username},"
                f"dataset_owner={dataset_owner}, dataset_name={dataset_name}")

    remote = RepoLocation(remote_url, logged_in_username)
    try:
        im = InventoryManager(config_file=config_file)

        try:
            # Check for dataset already existing in the user's working directory
            im.load_dataset(logged_in_username, dataset_owner, dataset_name)
            logger.info(f"{logged_in_username}/{dataset_owner}/{dataset_name} exists. Skipping auto-import.")
            return
        except InventoryException:
            # Dataset not found, import it
            logger.info(f"{logged_in_username}/{dataset_owner}/{dataset_name} not found. "
                        f"Auto-importing remote dataset from {remote_url}")
            config_obj = Configuration(config_file=config_file)

            # TODO gigantum/ideas#11: this token logic is NOT duplicated in the standard dataset or labbook flows. It
            #  could be handled in gitworkflows_utils.clone_repo below, or somewhere in a git auth logic module/object.
            #  Note that some complexity derives from the fact that we don't have access to the Flask session here.
            if access_token:
                if not id_token:
                    raise ValueError("Access and ID tokens are required to initialize git credentials")

                # If the access token is set, git creds should be configured

                try:
                    hub_api = config_obj.config['git']['remotes'][remote.host]['hub_api']
                except KeyError:
                    raise ValueError(f"Failed to configure git service URL based on target remote: {remote.host}")

                gl_mgr = GitLabManager(remote.host, hub_api=hub_api,
                                       access_token=access_token, id_token=id_token)
                gl_mgr.configure_git_credentials(remote.host, logged_in_username)

            gitworkflows_utils.clone_repo(remote_url=remote.remote_location, username=logged_in_username, owner=dataset_owner,
                                          load_repository=im.load_dataset_from_directory,
                                          put_repository=im.put_dataset)
            logger.info(f"{logged_in_username}/{dataset_owner}/{dataset_name} auto-imported successfully")

    except Exception as err:
        logger.error(f"(Job {p}) Error in check_and_import_dataset job")
        logger.exception(err)
        raise


def push_dataset_objects(objs: List[PushObject], logged_in_username: str, access_token: str, id_token: str,
                         dataset_owner: str, dataset_name: str, config_file: str = None) -> None:
    """Method to pull a collection of objects from a dataset's backend

    Args:
        objs: List if file PushObject to push
        logged_in_username: username for the currently logged in user
        access_token: bearer token
        id_token: identity token
        dataset_owner: Owner of the dataset containing the files to download
        dataset_name: Name of the dataset containing the files to download
        config_file: config file (used for test mocking)

    Returns:
        str: directory path of imported labbook
    """
    logger = LMLogger.get_logger()

    def progress_update_callback(completed_bytes: int) -> None:
        """Method to update the job's metadata and provide feedback to the UI"""
        current_job = get_current_job()
        if not current_job:
            return
        if 'completed_bytes' not in current_job.meta:
            current_job.meta['completed_bytes'] = 0

        current_job.meta['completed_bytes'] = int(current_job.meta['completed_bytes']) + completed_bytes
        current_job.save_meta()

    try:
        p = os.getpid()
        logger.info(f"(Job {p}) Starting push_dataset_objects(logged_in_username={logged_in_username},"
                    f"dataset_owner={dataset_owner}, dataset_name={dataset_name}")

        im = InventoryManager(config_file=config_file)
        ds = im.load_dataset(logged_in_username, dataset_owner, dataset_name)

        ds.namespace = dataset_owner
        ds.backend.set_default_configuration(logged_in_username, access_token, id_token)
        m = Manifest(ds, logged_in_username)
        iom = IOManager(ds, m)

        result = iom.push_objects(objs, progress_update_fn=progress_update_callback)

        job = get_current_job()
        if job:
            job.meta['failures'] = ",".join([f"{x.object_path}|{x.dataset_path}|{x.revision}" for x in result.failure])
            job.meta['message'] = result.message
            job.save_meta()

    except Exception as err:
        logger.exception(err)
        raise


def pull_objects(keys: List[str], logged_in_username: str, access_token: str, id_token: str,
                 dataset_owner: str, dataset_name: str,
                 labbook_owner: Optional[str] = None, labbook_name: Optional[str] = None,
                 config_file: str = None) -> None:
    """Method to pull a collection of objects from a dataset's backend.

    This runs the IOManager.pull_objects() method with `link_revision=False`. This is because this job can be run in
    parallel multiple times with different sets of keys. You don't want to link until the very end, which is handled
    in the `download_dataset_files` job, which is what scheduled this job.

    Args:
        keys: List if file keys to download
        logged_in_username: username for the currently logged in user
        access_token: bearer token
        id_token: identity token
        dataset_owner: Owner of the dataset containing the files to download
        dataset_name: Name of the dataset containing the files to download
        labbook_owner: Owner of the labbook if this dataset is linked
        labbook_name: Name of the labbook if this dataset is linked
        config_file: config file (used for test mocking)

    Returns:
        str: directory path of imported labbook
    """
    logger = LMLogger.get_logger()

    def progress_update_callback(completed_bytes: int) -> None:
        """Method to update the job's metadata and provide feedback to the UI"""
        current_job = get_current_job()
        if not current_job:
            return
        if 'completed_bytes' not in current_job.meta:
            current_job.meta['completed_bytes'] = 0

        current_job.meta['completed_bytes'] = int(current_job.meta['completed_bytes']) + completed_bytes
        current_job.save_meta()

    try:
        p = os.getpid()
        logger.info(f"(Job {p}) Starting pull_objects(logged_in_username={logged_in_username},"
                    f"dataset_owner={dataset_owner}, dataset_name={dataset_name}, labbook_owner={labbook_owner},"
                    f" labbook_name={labbook_name}")

        im = InventoryManager(config_file=config_file)

        if labbook_owner is not None and labbook_name is not None:
            # This is a linked dataset, load repo from the Project
            lb = im.load_labbook(logged_in_username, labbook_owner, labbook_name)
            dataset_dir = os.path.join(lb.root_dir, '.gigantum', 'datasets', dataset_owner, dataset_name)
            ds = im.load_dataset_from_directory(dataset_dir)
        else:
            # this is a normal dataset. Load repo from working dir
            ds = im.load_dataset(logged_in_username, dataset_owner, dataset_name)

        ds.namespace = dataset_owner
        ds.backend.set_default_configuration(logged_in_username, access_token, id_token)
        m = Manifest(ds, logged_in_username)
        iom = IOManager(ds, m)

        result = iom.pull_objects(keys=keys, progress_update_fn=progress_update_callback, link_revision=False)

        job = get_current_job()
        if job:
            job.meta['failure_keys'] = ",".join([x.dataset_path for x in result.failure])
            job.meta['message'] = result.message
            job.save_meta()

    except Exception as err:
        logger.exception(err)
        raise


def download_dataset_files(logged_in_username: str, access_token: str, id_token: str,
                           dataset_owner: str, dataset_name: str,
                           labbook_owner: Optional[str] = None, labbook_name: Optional[str] = None,
                           all_keys: Optional[bool] = False, keys: Optional[List[str]] = None,
                           config_file: str = None) -> None:
    """Method to download files from a dataset in the background and provide status to the UI.

    This job schedules `pull_objects` jobs after splitting up the download work into batches. At the end, the job
    removes any partially downloaded files (due to failures) and links all the files for the dataset.

    Args:
        logged_in_username: username for the currently logged in user
        access_token: bearer token
        id_token: identity token
        dataset_owner: Owner of the dataset containing the files to download
        dataset_name: Name of the dataset containing the files to download
        labbook_owner: Owner of the labbook if this dataset is linked
        labbook_name: Name of the labbook if this dataset is linked
        all_keys: Boolean indicating if all remaining files should be downloaded
        keys: List if file keys to download
        config_file: config file (used for test mocking)

    Returns:
        str: directory path of imported labbook
    """
    dispatcher_obj = Dispatcher()

    def update_feedback(msg: str, has_failures: Optional[bool] = None, failure_detail: Optional[str] = None,
                        percent_complete: Optional[float] = None) -> None:
        """Method to update the job's metadata and provide feedback to the UI"""
        current_job = get_current_job()
        if not current_job:
            return
        if has_failures:
            current_job.meta['has_failures'] = has_failures
        if failure_detail:
            current_job.meta['failure_detail'] = failure_detail
        if percent_complete:
            current_job.meta['percent_complete'] = percent_complete

        current_job.meta['feedback'] = msg
        current_job.save_meta()
    logger = LMLogger.get_logger()

    try:
        p = os.getpid()
        logger.info(f"(Job {p}) Starting download_dataset_files(logged_in_username={logged_in_username},"
                    f" dataset_owner={dataset_owner}, dataset_name={dataset_name}, labbook_owner={labbook_owner},"
                    f" labbook_name={labbook_name}, all_keys={all_keys}, keys={keys}")

        im = InventoryManager(config_file=config_file)

        if labbook_owner is not None and labbook_name is not None:
            # This is a linked dataset, load repo from the Project
            lb = im.load_labbook(logged_in_username, labbook_owner, labbook_name)
            dataset_dir = os.path.join(lb.root_dir, '.gigantum', 'datasets', dataset_owner, dataset_name)
            ds = im.load_dataset_from_directory(dataset_dir)
        else:
            # this is a normal dataset. Load repo from working dir
            ds = im.load_dataset(logged_in_username, dataset_owner, dataset_name)

        ds.namespace = dataset_owner
        ds.backend.set_default_configuration(logged_in_username, access_token, id_token)
        m = Manifest(ds, logged_in_username)
        iom = IOManager(ds, m)

        key_batches, total_bytes, num_files = iom.compute_pull_batches(keys, pull_all=all_keys)

        failure_keys = list()
        if key_batches:
            # Schedule jobs for batches
            bg_jobs = list()
            for keys in key_batches:
                job_kwargs = {
                    'keys': keys,
                    'logged_in_username': logged_in_username,
                    'access_token': access_token,
                    'id_token': id_token,
                    'dataset_owner': dataset_owner,
                    'dataset_name': dataset_name,
                    'labbook_owner': labbook_owner,
                    'labbook_name': labbook_name,
                    'config_file': config_file,
                }
                job_metadata = {'dataset': f"{logged_in_username}|{dataset_owner}|{dataset_name}",
                                'method': 'pull_objects'}

                job_key = dispatcher_obj.dispatch_task(method_reference=pull_objects,
                                                       kwargs=job_kwargs,
                                                       metadata=job_metadata,
                                                       persist=True)
                bg_jobs.append(BackgroundDownloadJob(dispatcher_obj, keys, job_key))

            update_feedback(f"Please wait - Downloading {num_files} files ({format_size(total_bytes)}) - 0% complete",
                            percent_complete=0,
                            has_failures=False)
            logger.info(f"(Job {p}) Starting file downloads for"
                        f" {logged_in_username}/{dataset_owner}/{dataset_name} with {len(key_batches)} jobs")

            while sum([(x.is_complete or x.is_failed) for x in bg_jobs]) != len(bg_jobs):
                # Refresh all job statuses and update status feedback
                [j.refresh_status() for j in bg_jobs]
                total_completed_bytes = sum([j.completed_bytes for j in bg_jobs])
                pc = (float(total_completed_bytes) / float(total_bytes)) * 100
                update_feedback(f"Please wait - Downloading {num_files} files ({format_size(total_completed_bytes)} of "
                                f"{format_size(total_bytes)}) - {round(pc)}% complete",
                                percent_complete=pc)
                time.sleep(1)

            # Aggregate failures if they exist
            for j in bg_jobs:
                if j.is_failed:
                    # Whole job failed...assume entire batch should get re-uploaded for now
                    failure_keys.extend(j.keys)
                else:
                    failure_keys.extend(j.get_failed_keys())

        # Set final status for UI
        if len(failure_keys) == 0:
            update_feedback(f"Download complete!", percent_complete=100, has_failures=False)
        else:
            failure_str = ""
            for f in failure_keys:
                # If any failed files partially downloaded, remove them.
                abs_dataset_path = os.path.join(m.current_revision_dir, f)
                abs_object_path = m.dataset_to_object_path(f)
                if os.path.exists(abs_dataset_path):
                    os.remove(abs_dataset_path)
                if os.path.exists(abs_object_path):
                    os.remove(abs_object_path)
                failure_str = f"{failure_str}{f}\n"

            failure_detail_str = f"Files that failed to download:\n{failure_str}"
            update_feedback("", has_failures=True, failure_detail=failure_detail_str)

        # Link dataset files, so anything that was successfully pulled will materialize
        m.link_revision()

        if len(failure_keys) > 0:
            # If any downloads failed, exit non-zero to the UI knows there was an error
            raise IOError(f"{len(failure_keys)} file(s) failed to download. Check message detail and try again.")

    except Exception as err:
        logger.exception(err)
        raise
