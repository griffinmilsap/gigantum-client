import os
import logging
import time

import selenium

import testutils
from testutils import graphql_helpers


def test_link_unpublished_dataset_then_publish_project(driver: selenium.webdriver, *args, **kwargs):
    """
    Test:
     1. A dataset can be created and linked to a project
     2. The dataset and project can be published together as private with a collaborator
     3. The collaborator can import the project and view the linked dataset

    Args:
         driver
    """
    username = testutils.log_in(driver)
    testutils.GuideElements(driver).remove_guide()

    # Create a dataset
    dataset_elts = testutils.DatasetElements(driver)
    dataset_title = dataset_elts.create_dataset()

    # Create a project and link the dataset
    driver.get(os.environ['GIGANTUM_HOST'])
    r = testutils.prep_py3_minimal_base(driver, skip_login=True)
    _, project_title = r.username, r.project_name
    driver.get(f"{os.environ['GIGANTUM_HOST']}/projects/{username}/{project_title}/inputData")
    file_browser_elts = testutils.FileBrowserElements(driver)
    file_browser_elts.file_browser_area.wait_to_appear(15)
    file_browser_elts.link_dataset(dataset_title, project_title)

    assert file_browser_elts.linked_dataset_card_name.find().text == dataset_title, \
        f"Dataset {dataset_title} was not linked successfully to project {project_title}"

    # Publish the dataset and project as private and add collaborator (read permissions)
    dataset_elts.publish_private_project_with_unpublished_linked_dataset(username, project_title, dataset_title)
    # Add collaborator to project
    cloud_project_elts = testutils.CloudProjectElements(driver)
    collaborator = cloud_project_elts.add_collaborator_with_permissions(project_title)
    # Add collaborator to dataset
    driver.get(f"{os.environ['GIGANTUM_HOST']}/datasets/{username}/{dataset_title}")
    time.sleep(10)
    cloud_project_elts.add_collaborator_with_permissions(dataset_title)
    # Log out
    side_bar_elts = testutils.SideBarElements(driver)
    side_bar_elts.do_logout(username)

    # Collaborator logs in and imports the project
    logging.info(f"Logging in as {collaborator}")
    username2 = testutils.log_in(driver, user_index=1)
    side_bar_elts.projects_icon.wait_to_appear()
    try:
        testutils.GuideElements.remove_guide(driver)
    except:
        pass
    logging.info(f"Navigating to {collaborator}'s cloud tab")
    driver.get(f"{os.environ['GIGANTUM_HOST']}/projects/cloud")
    cloud_project_elts.first_cloud_project.wait_to_appear(30)
    # This was added for dev cloud, may no longer be needed
    driver.refresh()
    cloud_project_elts.first_cloud_project.wait_to_appear(30)

    assert project_title == cloud_project_elts.first_cloud_project.find().text, \
        f"Expected {project_title} to be the first cloud project in {collaborator}'s cloud tab, " \
        f"but instead got {cloud_project_elts.first_cloud_project.find().text}"

    cloud_project_elts.import_first_cloud_project_button.click()
    project_control = testutils.ProjectControlElements(driver)
    project_control.container_status_stopped.wait_to_appear(30)

    # Collaborator checks that they can view linked dataset
    driver.get(f"{os.environ['GIGANTUM_HOST']}/projects/{username}/{project_title}/inputData")
    file_browser_elts.linked_dataset_card_name.wait_to_appear(30)

    assert file_browser_elts.linked_dataset_card_name.find().text == dataset_title, \
        f"Linked dataset {dataset_title} does not appear in input data for imported project {project_title}"

    side_bar_elts = testutils.SideBarElements(driver)
    side_bar_elts.do_logout(username2)

    # Log back in as user 1 so remote cleanup works OK.
    testutils.log_in(driver)


def test_link_published_dataset_then_publish_project(driver: selenium.webdriver, *args, **kwargs):
    """
    Test:
     1. A dataset can be published as private with a collaborator then linked to a project
     2. The project can be published as private with the same collaborator
     3. The collaborator can import the project and view the linked dataset

    Args:
        driver
    """
    username = testutils.log_in(driver)
    testutils.GuideElements(driver).remove_guide()

    # Publish a dataset as private with a collaborator (read permissions)
    dataset_elts = testutils.DatasetElements(driver)
    dataset_title = dataset_elts.create_dataset()

    dataset_elts.publish_dataset(dataset_title)
    cloud_project_elts = testutils.CloudProjectElements(driver)
    cloud_project_elts.add_collaborator_with_permissions(dataset_title)

    # Create a project and link the dataset
    driver.get(os.environ['GIGANTUM_HOST'])
    r = testutils.prep_py3_minimal_base(driver, skip_login=True)
    _, project_title = r.username, r.project_name
    driver.get(f"{os.environ['GIGANTUM_HOST']}/projects/{username}/{project_title}/inputData")
    file_browser_elts = testutils.FileBrowserElements(driver)
    file_browser_elts.file_browser_area.wait_to_appear(15)
    file_browser_elts.link_dataset(dataset_title, project_title)

    assert file_browser_elts.linked_dataset_card_name.find().text == dataset_title, \
        f"Dataset {dataset_title} was not linked successfully to project {project_title}"

    # Publish the project as private and add same collaborator (read permissions)
    time.sleep(3)
    cloud_project_elts.publish_private_project(project_title)
    collaborator = cloud_project_elts.add_collaborator_with_permissions(project_title)
    side_bar_elts = testutils.SideBarElements(driver)
    side_bar_elts.do_logout(username)

    # Collaborator logs in and imports the project
    logging.info(f"Logging in as {collaborator}")
    username2 = testutils.log_in(driver, user_index=1)
    side_bar_elts.projects_icon.wait_to_appear()
    try:
        testutils.GuideElements.remove_guide(driver)
    except:
        pass
    logging.info(f"Navigating to {collaborator}'s cloud tab")
    driver.get(f"{os.environ['GIGANTUM_HOST']}/projects/cloud")
    cloud_project_elts.first_cloud_project.wait_to_appear(30)
    # Temporary for dev cloud
    driver.refresh()
    cloud_project_elts.first_cloud_project.wait_to_appear(30)

    assert project_title == cloud_project_elts.first_cloud_project.find().text, \
        f"Expected {project_title} to be the first cloud project in {collaborator}'s cloud tab, " \
        f"but instead got {cloud_project_elts.first_cloud_project.find().text}"

    cloud_project_elts.import_first_cloud_project_button.click()
    project_control = testutils.ProjectControlElements(driver)
    project_control.container_status_stopped.wait_to_appear(30)

    # Collaborator checks that they can view linked dataset
    driver.get(f"{os.environ['GIGANTUM_HOST']}/projects/{username}/{project_title}/inputData")
    file_browser_elts.linked_dataset_card_name.wait_to_appear(30)

    assert file_browser_elts.linked_dataset_card_name.find().text == dataset_title, \
        f"Linked dataset {dataset_title} does not appear in input data for imported project {project_title}"

    side_bar_elts = testutils.SideBarElements(driver)
    side_bar_elts.do_logout(username2)

    # Log back in as user 1 so remote cleanup works OK.
    testutils.log_in(driver)
