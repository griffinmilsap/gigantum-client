import os
import logging

import selenium

import testutils


def test_project_file_browser(driver: selenium.webdriver, *args, **kwargs):
    """
    Test that a file can be dragged and dropped into code, input data,
    and output data in a project.

    Args:
        driver
    """
    r = testutils.prep_py3_minimal_base(driver)
    username, project_title = r.username, r.project_name

    logging.info(f"Navigating to code for project {project_title}")
    driver.get(f"{os.environ['GIGANTUM_HOST']}/projects/{username}/{project_title}/code")
    file_browser_elts = testutils.FileBrowserElements(driver)
    file_browser_elts.file_browser_area.wait_to_appear()
    logging.info(f"Dragging and dropping a file into code for project {project_title}")
    file_browser_elts.drag_drop_file_in_drop_zone()

    assert file_browser_elts.file_information.find().text == "sample-upload.txt", \
        "Expected sample-upload.txt to be the first file in code"

    logging.info(f"Navigating to input data for project: {project_title}")
    driver.get(f"{os.environ['GIGANTUM_HOST']}/projects/{username}/{project_title}/inputData")
    file_browser_elts.file_browser_area.wait_to_appear()
    logging.info(f"Dragging and dropping file into input data for project {project_title}")
    file_browser_elts.drag_drop_file_in_drop_zone()

    assert file_browser_elts.file_information.find().text == "sample-upload.txt", \
        "Expected sample-upload.txt to be the first file in input data"

    logging.info(f"Navigating to output data for project: {project_title}")
    driver.get(f"{os.environ['GIGANTUM_HOST']}/projects/{username}/{project_title}/outputData")
    file_browser_elts.untracked_directory.wait_to_appear()
    logging.info(f"Dragging and dropping file into the untracked directory in output data for project {project_title}")
    file_browser_elts.drag_drop_file_in_drop_zone(output_data_target=True)

    assert file_browser_elts.file_information.find().text == "sample-upload.txt", \
        "Expected sample-upload.txt to be the first file in Output Data"


def test_rename_file_project_file_browser(driver: selenium.webdriver, *args, **kwargs):
    """
    Test that a file can be renamed.

    Args:
        driver
    """
    r = testutils.prep_py3_minimal_base(driver)
    username, project_title = r.username, r.project_name

    file_browser_elts = testutils.FileBrowserElements(driver)
    logging.info(f"Navigating to input data for project: {project_title}")
    driver.get(f"{os.environ['GIGANTUM_HOST']}/projects/{username}/{project_title}/inputData")
    file_browser_elts.file_browser_area.wait_to_appear()
    logging.info(f"Dragging and dropping file into input data for project {project_title}")
    file_browser_elts.drag_drop_file_in_drop_zone()

    assert file_browser_elts.file_information.find().text == "sample-upload.txt", \
        "Expected sample-upload.txt to be the first file in input data"

    file_browser_elts.rename_file_button().click()
    file_browser_elts.rename_input_file("sample-upload.txt", "_rename")
    file_browser_elts.confirm_file_rename_button().click()
    driver.refresh()
    file_browser_elts.file_information.wait_to_appear()

    assert file_browser_elts.file_information.find().text == "sample-upload.txt_rename", \
        f"Expected sample-upload.txt to be renamed to sample-upload.txt_rename, but instead got " \
        f"{file_browser_elts.file_information.find().text}"


def test_delete_file_project_file_browser(driver: selenium.webdriver, *args, **kwargs):
    """
    Test that a file can be dragged and dropped into input data and deleted properly.

    Args:
        driver
    """
    r = testutils.prep_py3_minimal_base(driver)
    username, project_title = r.username, r.project_name

    file_browser_elts = testutils.FileBrowserElements(driver)
    logging.info(f"Navigating to input data for project: {project_title}")
    driver.get(f"{os.environ['GIGANTUM_HOST']}/projects/{username}/{project_title}/inputData")
    file_browser_elts.file_browser_area.wait_to_appear()
    logging.info(f"Dragging and dropping file into input data for project {project_title}")
    file_browser_elts.drag_drop_file_in_drop_zone()

    assert file_browser_elts.file_information.find().text == "sample-upload.txt", \
        "Expected sample-upload.txt to be the first file in input data"

    file_browser_elts.trash_can_button().click()
    file_browser_elts.confirm_delete_file_button().click()
    driver.refresh()
    file_browser_elts.file_browser_area.wait_to_appear()

    # Expect to be empty
    file_contents = file_browser_elts.input_file_browser_contents_list
    assert len(file_contents) == 1, "Expected file browser to be empty but more than 1 file/directory exists"
    assert file_contents[0] == 'untracked', "Expected file browser to be empty, but still have untracked folder"

               
def test_dataset_file_browser(driver: selenium.webdriver, *args, **kwargs):
    """
    Test that a file can be dragged and dropped into data in a dataset.

    Args:
        driver
    """
    username = testutils.log_in(driver)
    testutils.GuideElements(driver).remove_guide()
    dataset_elts = testutils.DatasetElements(driver)
    dataset_title = dataset_elts.create_dataset()

    logging.info(f"Navigating to data for dataset {dataset_title}")
    driver.get(f"{os.environ['GIGANTUM_HOST']}/datasets/{username}/{dataset_title}/data")
    file_browser_elts = testutils.FileBrowserElements(driver)
    file_browser_elts.file_browser_area.wait_to_appear()
    logging.info(f"Dragging and dropping file into data for dataset {dataset_title}")
    file_browser_elts.drag_drop_file_in_drop_zone()

    assert file_browser_elts.file_information.find().text == 'sample-upload.txt', \
        "Expected sample-upload.txt to be the first file in Data"
