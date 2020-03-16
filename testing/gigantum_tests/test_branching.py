import os
import logging
import time

import selenium

import testutils


def test_create_local_branch(driver: selenium.webdriver, *args, **kwargs):
    """
    Test the creation of a local branch.

    Args:
        driver
    """
    r = testutils.prep_py3_minimal_base(driver)
    username, project_name = r.username, r.project_name

    branch_elts = testutils.BranchElements(driver)
    branch_elts.create_local_branch("test-branch")

    logging.info("Checking that you are on the new branch and that the new branch is local only")

    assert branch_elts.upper_left_branch_name.find().text == "test-branch", \
        "Expected to be on test-branch, upper left"
    assert branch_elts.upper_left_branch_local_only.find(), "Expected test-branch to be local only, upper left"

    branch_elts.manage_branches_button.wait_to_appear().click()
    branch_elts.manage_branches_modal.wait_to_appear()

    assert branch_elts.manage_branches_branch_name.find().text == "test-branch", \
        "Expected to be on test-branch, manage branches"
    assert branch_elts.manage_branches_local_only.find(), "Expected test-branch to be local only, manage branches"


def test_delete_file_local_branch(driver: selenium.webdriver, *args, **kwargs):
    """
    Test that a file created on the master branch, deleted in a local branch, and then merged back into the
    master branch does not appear in the master branch.

    Args:
        driver
    """
    r = testutils.prep_py3_minimal_base(driver)
    username, project_title = r.username, r.project_name

    logging.info("Navigating to input data tab")
    driver.get(f"{os.environ['GIGANTUM_HOST']}/projects/{username}/{project_title}/inputData")

    logging.info("Adding a file in input data tab while on master branch")
    file_browser_elts = testutils.FileBrowserElements(driver)
    file_browser_elts.file_browser_area.wait_to_appear()
    file_browser_elts.drag_drop_file_in_drop_zone()

    branch_elts = testutils.BranchElements(driver)
    branch_elts.create_local_branch("test-branch")

    contents = file_browser_elts.input_file_browser_contents_list
    assert len(contents) == 2, "Expected sample-upload.txt to appear in test-branch before deletion"
    assert contents[0] == 'untracked', "Expected sample-upload.txt to appear in test-branch before deletion"
    assert contents[1] == 'sample-upload.txt', "Expected sample-upload.txt to appear in test-branch before deletion"

    logging.info("Deleting the file in input data tab while on test-branch")
    file_browser_elts.trash_can_button.wait_to_appear().click()
    file_browser_elts.confirm_delete_file_button.wait_to_appear().click()
    file_browser_elts.confirm_delete_file_button.wait_to_disappear()
    # Time sleep is consistent and necessary
    time.sleep(5)

    logging.info("Switching back to master branch and merging test-branch")
    branch_elts.switch_to_alternate_branch()
    branch_elts.merge_alternate_branch()

    logging.info(f"Checking that file deleted in input data tab while on test-branch does not appear in master branch")

    contents = file_browser_elts.input_file_browser_contents_list
    assert len(contents) == 1, "Expected sample-upload.txt to not appear in master branch"
    assert contents[0] == 'untracked', "Expected sample-upload.txt to not appear in master branch"
