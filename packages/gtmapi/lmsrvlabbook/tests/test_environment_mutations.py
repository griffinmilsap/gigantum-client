# Copyright (c) 2017 FlashX, LLC
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
import pytest
import time
from docker.errors import ImageNotFound
import getpass
import pprint

from gtmcore.configuration import get_docker_client
from gtmcore.inventory.inventory import InventoryManager
from lmsrvlabbook.tests.fixtures import fixture_working_dir_env_repo_scoped
from lmsrvcore.auth.user import get_logged_in_username
from gtmcore.environment import ComponentManager
from gtmcore.fixtures import ENV_UNIT_TEST_REPO, ENV_UNIT_TEST_BASE, ENV_UNIT_TEST_REV


TIMEOUT_MAX = 45


@pytest.fixture
def reset_images(request):
    """A pytest fixture that checks if the test images exist and deletes them"""
    # Clean up images
    client = get_docker_client()

    # image should never exist before the test starts
    image_name = "gmlb-{}-{}".format(get_logged_in_username(), f'default-{request.param}')
    try:
        client.images.get(image_name)
        client.images.remove(image_name)
        raise ValueError("Test image exists before test started. Attempting to automatically removing image. Run again")
    except ImageNotFound:
        pass

    yield None

    try:
        client.images.get(image_name)
        client.images.remove(image_name)
    except ImageNotFound:
        pass


class TestEnvironmentMutations(object):
    @pytest.mark.parametrize('reset_images', ["labbook-build1"], indirect=['reset_images'])
    def test_build_image(self, fixture_working_dir_env_repo_scoped, reset_images):
        """Test building a labbook's image"""
        im = InventoryManager(fixture_working_dir_env_repo_scoped[0])
        lb = im.create_labbook("default", "default", "labbook-build1",
                               description="building an env")
        cm = ComponentManager(lb)
        cm.add_base(ENV_UNIT_TEST_REPO, "ut-busybox", 0)

        query = """
        {
            labbook(name: "labbook-build1", owner: "default") {
                environment {
                    imageStatus
                    containerStatus
                }
            }
        }
        """

        r = fixture_working_dir_env_repo_scoped[2].execute(query)
        assert 'errors' not in r
        assert r['data']['labbook']['environment']['imageStatus'] == 'DOES_NOT_EXIST'
        assert r['data']['labbook']['environment']['containerStatus'] == 'NOT_RUNNING'

        # Build the image
        build_query = """
        mutation myBuildImage {
          buildImage(input: {labbookName: "labbook-build1", owner: "default"}) {
            environment {
              imageStatus
              containerStatus
            }
          }
        }
        """

        r = fixture_working_dir_env_repo_scoped[2].execute(build_query)
        import pprint;
        pprint.pprint(r)
        assert 'errors' not in r

        assert r['data']['buildImage']['environment']['imageStatus'] in ['BUILD_QUEUED', 'BUILD_IN_PROGRESS']
        assert r['data']['buildImage']['environment']['containerStatus'] == 'NOT_RUNNING'

        ## Sneak in a test for background jobs
        get_bg_jobs_query = """
        {
            labbook(name: "labbook-build1", owner: "default") {
                backgroundJobs {
                    jobKey
                    status
                    failureMessage
                    jobMetadata
                    startedAt
                    result
                }
            }
        }
        """
        r = fixture_working_dir_env_repo_scoped[2].execute(get_bg_jobs_query)
        assert 'errors' not in r, "There should be no errors when querying for background job status"
        assert r['data']['labbook']['backgroundJobs'][0]['status'], "Background Jobs status query should not be None"
        pprint.pprint(r)

        # Wait for build to succeed for up to TIMEOUT_MAX seconds
        success = False
        for _ in range(TIMEOUT_MAX):
            result = fixture_working_dir_env_repo_scoped[2].execute(query)
            if result['data']['labbook']['environment']['imageStatus'] == 'EXISTS':
                success = True
                break
            assert result['data']['labbook']['environment']['imageStatus'] == 'BUILD_IN_PROGRESS'
            time.sleep(1)

        r = fixture_working_dir_env_repo_scoped[2].execute(get_bg_jobs_query)
        assert 'errors' not in r
        assert r['data']['labbook']['backgroundJobs'][0]['status'] == 'finished'
        assert r['data']['labbook']['backgroundJobs'][0]['result'].isalnum()
        assert 'build_image' in r['data']['labbook']['backgroundJobs'][0]['jobMetadata']
        pprint.pprint(r)

        assert success is True, f"Failed to build within {TIMEOUT_MAX} second timeout."

        r = fixture_working_dir_env_repo_scoped[2].execute(query)
        assert 'errors' not in r
        assert r['data']['labbook']['environment']['imageStatus'] == 'EXISTS'
        assert r['data']['labbook']['environment']['containerStatus'] == 'NOT_RUNNING'

    @pytest.mark.parametrize('reset_images', ["labbook-build2"], indirect=['reset_images'])
    def test_build_image_no_cache(self, fixture_working_dir_env_repo_scoped, reset_images):
        """Test building a labbook's image"""
        im = InventoryManager(fixture_working_dir_env_repo_scoped[0])
        lb = im.create_labbook("default", "default", "labbook-build2",
                               description="building an env")
        cm = ComponentManager(lb)
        cm.add_base(ENV_UNIT_TEST_REPO, "ut-busybox", 0)

        query = """
        {
            labbook(name: "labbook-build2", owner: "default") {
                environment {
                    imageStatus
                    containerStatus
                }
            }
        }
        """

        r = fixture_working_dir_env_repo_scoped[2].execute(query)
        assert 'errors' not in r
        assert r['data']['labbook']['environment']['imageStatus'] == 'DOES_NOT_EXIST'
        assert r['data']['labbook']['environment']['containerStatus'] == 'NOT_RUNNING'

        # Build the image
        build_query = """
        mutation myBuildImage {
          buildImage(input: {
            labbookName: "labbook-build2",
            owner: "default",
            noCache: true
          }) {
            environment {
              imageStatus
              containerStatus
            }
          }
        }
        """
        r = fixture_working_dir_env_repo_scoped[2].execute(build_query)
        assert 'errors' not in r
        assert r['data']['buildImage']['environment']['imageStatus'] in ['BUILD_QUEUED', 'BUILD_IN_PROGRESS']
        assert r['data']['buildImage']['environment']['containerStatus'] == 'NOT_RUNNING'

        # Wait for build to succeed for up to TIMEOUT_MAX seconds
        success = False
        for _ in range(TIMEOUT_MAX):
            result = fixture_working_dir_env_repo_scoped[2].execute(query)

            if result['data']['labbook']['environment']['imageStatus'] == 'EXISTS':
                success = True
                break

            assert result['data']['labbook']['environment']['imageStatus'] == 'BUILD_IN_PROGRESS'

            time.sleep(1)

        assert success is True, f"Failed to build within {TIMEOUT_MAX} second timeout."

        r = fixture_working_dir_env_repo_scoped[2].execute(query)
        assert 'errors' not in r
        assert r['data']['labbook']['environment']['imageStatus'] == 'EXISTS'
        assert r['data']['labbook']['environment']['containerStatus'] == 'NOT_RUNNING'

    @pytest.mark.parametrize('reset_images', ["labbook-build2"], indirect=['reset_images'])
    def test_cancel_build(self, fixture_working_dir_env_repo_scoped, reset_images):
        im = InventoryManager(fixture_working_dir_env_repo_scoped[0])
        lb = im.create_labbook("default", "default", "labbook-build-cancel",
                               description="building an env")
        cm = ComponentManager(lb)
        cm.add_base(ENV_UNIT_TEST_REPO, "ut-busybox", 0)
        cm.add_docker_snippet('customdocker', ['RUN sleep 2'])

        # Build the image
        build_query = """
        mutation myBuildImage {
          buildImage(input: {
            labbookName: "labbook-build-cancel",
            owner: "default",
            noCache: true
          }) {
            environment {
              imageStatus
              containerStatus
            }
          }
        }
        """
        r = fixture_working_dir_env_repo_scoped[2].execute(build_query)
        time.sleep(1)
        assert 'errors' not in r
        assert r['data']['buildImage']['environment']['imageStatus'] == 'BUILD_IN_PROGRESS'

        cancel_query = """
        mutation myCancel {
            cancelBuild(input: {
                labbookName: "labbook-build-cancel",
                owner: "default"
            }) {
                buildStopped
                message
            }
        }"""
        cancel_r = fixture_working_dir_env_repo_scoped[2].execute(cancel_query)
        assert 'errors' not in cancel_r
        assert cancel_r['data']['cancelBuild']['buildStopped'] == True

        check_query = """
        {
            labbook(name: "labbook-build-cancel", owner: "default") {
                environment {
                    imageStatus
                    containerStatus
                }
            }
        }
        """
        check_r = fixture_working_dir_env_repo_scoped[2].execute(check_query)
        pprint.pprint(check_r)
        assert 'errors' not in check_r
        assert check_r['data']['labbook']['environment']['imageStatus'] == 'BUILD_FAILED'
