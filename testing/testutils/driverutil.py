import os
import sys
import time
import json
import logging
import datetime
from typing import Any, Callable, List, Optional

import boto3
import requests
from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw

from .cleanup import delete_local_datasets, delete_projects_on_disk, delete_project_images, stop_project_containers
from .actions import list_remote_projects
from .graphql_helpers import delete_remote_project, list_remote_datasets, delete_dataset


class TestResult(object):
    name: str
    result: str
    value: Any
    duration: float
    fail_message: Optional[str] = None
    log_messages: Optional[List[str]] = None
    screenshot_path: Optional[str] = None

    def __init__(self, name: str, result: str, value: Any, duration: float,
                 fail_message=None, log_messages=None, screenshot_path=None):
        self.name = name
        self.result = result
        self.value = value
        self.duration = duration
        self.fail_message = fail_message
        self.log_messages = log_messages
        self.screenshot_path = screenshot_path

    def render(self) -> str:
        duration = f'({self.duration:.1f}sec)'
        line = f'{self.result:6s} {duration:10s} :: {self.name[:30]:31s} - {self.fail_message or self.result}'
        return line


class Playbook(object):

    def __init__(self, path, name, test_methods):
        self.path = path
        self.name = name
        self.test_methods = test_methods


def load_playbook(path: str) -> Playbook:
    name = path.replace('.py', '')
    playbook_pkg = __import__(name)
    test_methods = [getattr(playbook_pkg, field)
                    for field in dir(playbook_pkg)
                    if callable(getattr(playbook_pkg, field))
                    and 'test_' == field[:5]]
    return Playbook(path=path, name=name, test_methods=test_methods)


class TestRunner:
    def __init__(self):
        self.artifact_dir = self._set_artifact_dir()
        self.duration = 0
        self.results: List[TestResult] = []

    @property
    def gigantum_version(self):
        r = requests.get(f"{os.environ['GIGANTUM_HOST']}/api/ping")
        return json.loads(r.text)['revision']

    def __enter__(self):
        self._start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.duration = time.time() - self._start_time
        try:
            self._upload_to_s3()
        except Exception as e:
            logging.warning(f"Skipping upload to S3: {e}")

    def execute_test(self, test_method: Callable, driver, *args, **kwargs) -> TestResult:
        t0 = time.time()
        try:
            logging.info(f"Running test: {test_method.__name__}")
            value = test_method(driver, *args, **kwargs)
            result = TestResult(test_method.__name__, 'PASS', value, time.time()-t0)
            logging.info(f"PASSED {test_method.__name__}")
        except Exception as e:
            logging.warning(f"FAILED {test_method.__name__}: {e}")
            logging.exception(e)
            result = TestResult(test_method.__name__, 'FAIL', None, time.time()-t0,
                                fail_message=str(e))
            self._save_screenshot(driver, 'FAIL', e, test_method)
        finally:
            try:
                driver.get(f"{os.environ['GIGANTUM_HOST']}/api/ping")
                driver.execute_script(f'alert("{test_method.__name__} -- cleaning up");')
                self._cleanup(driver)
            except Exception as e:
                logging.error(f"Error cleaning up: {e}")
            driver.quit()

        self.results.append(result)
        return result

    @property
    def success(self):
        return all([r.result == 'PASS' for r in self.results])

    def render_results(self):
        pass_cnt = len(list(filter(lambda r: r.result == 'PASS', self.results)))
        fail_cnt = len(self.results) - pass_cnt
        print(f'\nResults: {pass_cnt} PASSED, {fail_cnt} FAILED of '
              f'{len(self.results)} TOTAL in {self.duration:.1f}sec')
        for result in self.results:
            print(result.render())
        print()

    def _set_artifact_dir(self):
        timestamp = datetime.datetime.utcnow().strftime('%Y-%m-%d_%H%M')
        artifact_dir = f'/tmp/gigantum_{timestamp}'
        os.makedirs(artifact_dir, exist_ok=True)
        return artifact_dir

    def _cleanup(self, driver):
        stop_project_containers()
        delete_project_images()
        delete_projects_on_disk()

        # Delete remote projects
        remote_projects = list_remote_projects()
        for owner, project_name in remote_projects:
            if 'selenium-project-' in project_name:
                delete_remote_project(owner, project_name)

        remote_datasets = list_remote_datasets()
        for owner, dataset_name in remote_datasets:
            if 'selenium-dataset-' in dataset_name:
                delete_dataset(owner, dataset_name)
        delete_local_datasets()

    def _upload_to_s3(self):
        s3client = boto3.resource('s3')
        bucket = s3client.Bucket(os.environ['S3_BUCKET_NAME'])

        name = self.artifact_dir.split('/')[-1]
        for artifact in os.listdir(self.artifact_dir):
            logging.info(f"Uploading file {artifact}")
            bucket.upload_file(os.path.join(self.artifact_dir, artifact),
                               os.path.join(name, artifact))

    def _save_screenshot(self, driver, fail_type, message, test_func):
        screenshot_fname = f'{test_func.__name__}--{fail_type}.png'
        screenshot_fname = f'{self.artifact_dir}/{screenshot_fname}'
        driver.save_screenshot(screenshot_fname)

        img = Image.open(screenshot_fname)
        draw = ImageDraw.Draw(img)
        font = ImageFont.truetype('Arial.ttf', 30)
        draw.text((100, 400), f'{fail_type}: {message}', font=font, fill=(255, 0, 0, 200))
        img.save(screenshot_fname)

    def _render_log(self, test_name, failure_type):
        logfile_path = os.path.join(os.environ['GIGANTUM_HOME'],
                                    '.labmanager', 'logs', 'labmanager.log')
        lines = open(logfile_path).readlines()[:15]
        parsed_lines = []
        for l in lines:
            d = json.loads(l)
            # Do not show log messages older than 10 minutes
            if time.time() - d['created'] > 600:
                continue
            parsed_lines.append(f"{d.get('levelname')} -- {d.get('filename')}::"
                                f"{d.get('funcName')}.{d.get('lineno')} -- "
                                f"{d.get('message')}")
        with open(os.path.join(self.artifact_dir, f"{test_name}.{failure_type}.log"), 'w') as lf:
            lf.write('\n'.join(parsed_lines))


def load_playbooks(test_root, path_list: List[str]) -> List[Playbook]:
    playbooks_dir = os.path.join(test_root, 'gigantum_tests')
    sys.path.append(playbooks_dir)

    if len(path_list) == 0:
        # If no explicit path list, get all test playbooks, but skip examples
        for test_file in os.listdir(playbooks_dir):
            if '.py' in test_file and 'test_examples.py' != test_file:
                yield load_playbook(test_file)
    else:
        for path in path_list:
            logging.info(f"START running playbook: {path}")
            if path and 'test_' == path[:5]:
                yield load_playbook(path)

