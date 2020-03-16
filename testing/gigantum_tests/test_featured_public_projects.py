import os
import logging

import selenium

import testutils
from testutils.graphql_helpers import delete_local_project


def test_import_projects_via_url(driver: selenium.webdriver, *args, **kwargs):
    """
    Test that featured public projects can be imported via url and that they build successfully.

    Args:
        driver
    """
    featured_public_projects = ["gigantum.com/meg297/military-expenditure-gdp-population",
                                "gigantum.com/gigantum-examples/scikit-learn-in-gigantum"]

    testutils.log_in(driver)
    testutils.GuideElements(driver).remove_guide()
    try:
        for project_url in featured_public_projects:
            import_project_elts = testutils.ImportProjectElements(driver)
            import_project_elts.import_project_via_url(project_url)
            project_control = testutils.ProjectControlElements(driver)

            assert project_control.container_status_stopped.find().is_displayed(), \
                f"Project {project_url} was not imported successfully via url"

            side_bar_elts = testutils.SideBarElements(driver)
            side_bar_elts.projects_icon.find().click()
            import_project_elts.import_existing_button.wait_to_appear(60)
    finally:
        for project_url in featured_public_projects:
            _, owner, project_title = project_url.split('/')
            try:
                delete_local_project(owner, project_title)
            except Exception as e:
                logging.error(f"Failed to delete project {owner}/{project_title}: {e}")


def test_import_projects_via_zip_file(driver: selenium.webdriver, *args, **kwargs):
    """
    Test that projects can be imported via zip file and that they build successfully.

    Args:
        driver
    """
    project_zip_file = "sample-prj-93f4b4.zip"
    file_path = os.path.abspath(os.path.join(__file__, f"../../../resources/{project_zip_file}"))
    username = testutils.log_in(driver)
    testutils.GuideElements(driver).remove_guide()
    try:
        import_project_elts = testutils.ImportProjectElements(driver)
        import_project_elts.import_project_via_zip_file_drag_and_drop(file_path)
        project_control = testutils.ProjectControlElements(driver)

        assert project_control.container_status_stopped.find().is_displayed(), \
            f"Project {project_zip_file} was not imported successfully via zip file"
    finally:
        try:
            delete_local_project(username, "sample-prj")
        except Exception as e:
            logging.error(f"Failed to delete project {username}/'sample-prj': {e}")
