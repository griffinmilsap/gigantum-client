import os
import logging
import time

import selenium

import testutils
from testutils import graphql_helpers, graphql_hub_helpers


def test_publish_sync_delete_project(driver: selenium.webdriver, *args, **kwargs):
    """
    Test that a project can be published, synced, and deleted.

    Args:
        driver
    """
    r = testutils.prep_py3_minimal_base(driver)
    username, project_title = r.username, r.project_name

    # Publish a project as private
    cloud_project_elts = testutils.CloudProjectElements(driver)
    cloud_project_elts.publish_private_project(project_title)

    logging.info(f"Navigating to {username}'s cloud tab")
    driver.get(f"{os.environ['GIGANTUM_HOST']}/projects/cloud")
    cloud_project_elts.first_cloud_project.wait_to_appear(30)

    logging.info(f"Checking if a remote is set for project {project_title}")
    cloud_project_stdout, cloud_project_stderr = cloud_project_elts.check_cloud_project_remote_git_repo(
        username, project_title)

    assert "https://" in cloud_project_stdout, f"Expected to see a remote set for project {project_title}, " \
                                               f"but got {cloud_project_stdout}"

    logging.info(f"Checking if project {project_title} appears in {username}'s cloud tab")
    first_cloud_project = cloud_project_elts.first_cloud_project.find().text
    logging.info(f"Found first cloud project {first_cloud_project}")

    assert project_title == first_cloud_project, \
        f"Expected {project_title} to be the first cloud project in {username}'s cloud tab, " \
        f"but instead got {first_cloud_project}"

    # Add a file and sync cloud project
    driver.get(f'{os.environ["GIGANTUM_HOST"]}/projects/{username}/{project_title}/inputData')
    file_browser_elts = testutils.FileBrowserElements(driver)
    file_browser_elts.file_browser_area.wait_to_appear()
    file_browser_elts.drag_drop_file_in_drop_zone()
    cloud_project_elts.sync_cloud_project(project_title)
    project_control_elts = testutils.ProjectControlElements(driver)

    assert "Sync complete" in project_control_elts.footer_notification_message.find().text, \
        "Expected 'Sync complete' in footer"

    # Delete cloud project
    cloud_project_elts.delete_cloud_project(project_title)

    # Assert project does not exist remotely (via GraphQL)
    assert not graphql_hub_helpers.repository_exists(username, project_title), \
        f"Expected project {project_title} to not exist remotely via GraphQL"

    # Assert that project does not have remote Git repo (use Git 2.20+)
    del_cloud_project_stdout, del_cloud_project_stderr = cloud_project_elts.check_cloud_project_remote_git_repo(
        username, project_title)

    assert "fatal" in del_cloud_project_stderr, f"Expected to not see a remote set for project {project_title}, " \
                                                f"but got {del_cloud_project_stderr}"

    # Assert project does not exist in cloud tab (NOTE: For this to work you must have at least 1 cloud project in
    # your first test user account!)
    time.sleep(2)
    first_cloud_project = cloud_project_elts.first_cloud_project.find().text

    assert project_title != first_cloud_project, \
        f"Expected {project_title} to not be the first cloud project in {username}'s Cloud tab, " \
        f"but instead got {first_cloud_project}"


def test_publish_collaborator(driver: selenium.webdriver, *args, ** kwargs):
    """
    Test that a project in Gigantum can be published, shared with a collaborator, and imported by the collaborator.

    Args:
        driver
    """
    r = testutils.prep_py3_minimal_base(driver)
    username, project_title = r.username, r.project_name

    # Publish a project as private
    cloud_project_elts = testutils.CloudProjectElements(driver)
    cloud_project_elts.publish_private_project(project_title)

    # Owner adds collaborator and logs out
    collaborator = cloud_project_elts.add_collaborator_with_permissions(project_title)
    side_bar_elts = testutils.SideBarElements(driver)
    side_bar_elts.do_logout(username)

    # Collaborator logs in, imports cloud project, and logs out
    logging.info(f"Logging in as {collaborator}")
    testutils.log_in(driver, user_index=1)
    side_bar_elts.projects_icon.wait_to_appear()
    try:
        testutils.GuideElements.remove_guide(driver)
    except:
        pass
    logging.info(f"Navigating to {collaborator}'s cloud tab")
    driver.get(f"{os.environ['GIGANTUM_HOST']}/projects/cloud")
    cloud_project_elts.first_cloud_project.wait_to_appear(30)
    first_cloud_project = cloud_project_elts.first_cloud_project.find().text

    assert project_title == first_cloud_project, \
        f"Expected {project_title} to be the first cloud project in {collaborator}'s cloud tab, " \
        f"but instead got {first_cloud_project}"

    cloud_project_elts.import_first_cloud_project_button.click()
    project_control = testutils.ProjectControlElements(driver)
    project_control.container_status_stopped.wait_to_appear(30)
    shared_project_title = cloud_project_elts.project_overview_project_title.find().text

    assert project_title in shared_project_title, \
        f"After import, expected project {project_title} to open to project overview page"

    side_bar_elts.do_logout(collaborator)

    # Owner logs in and deletes cloud project
    logging.info(f"Logging in as {username}")
    testutils.log_in(driver)
    side_bar_elts.projects_icon.wait_to_appear()
    try:
        testutils.GuideElements.remove_guide(driver)
    except:
        pass
    cloud_project_elts.delete_cloud_project(project_title)

    # Assert project does not exist remotely (via GraphQL)
    assert not graphql_hub_helpers.repository_exists(username, project_title), \
        f"Expected project {project_title} to not exist remotely via GraphQL"

    # Assert that cloud project does not have remote Git repo (use Git 2.20+)
    del_cloud_project_stdout, del_cloud_project_stderr = cloud_project_elts.check_cloud_project_remote_git_repo(
        username, project_title)

    assert "fatal" in del_cloud_project_stderr, f"Expected to not see a remote set for project {project_title}, " \
                                                f"but got {del_cloud_project_stderr}"

