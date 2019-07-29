import logging
import time

import selenium
from selenium.webdriver.common.by import By

import testutils
import os


def test_featured_public_projects(driver: selenium.webdriver, *args, **kwargs):
    """
    Test that featured public projects import and build successfully.
    """

    try:
        # Log in and remove guide
        testutils.log_in(driver)
        testutils.GuideElements(driver).remove_guide()
        # Import featured public projects
        # TODO - add in gigantum.com/randal/baltimore-sun-data-bridge-data
        featured_public_projects = ["gigantum.com/meg297/military-expenditure-gdp-population",
                                    "gigantum.com/billvb/fsw-telecoms-study"]
        for project in featured_public_projects:
            logging.info(f"Importing featured public project: {project}")
            import_project_elts = testutils.ImportProjectElements(driver)
            import_project_elts.import_project_via_url(project)
            project_control = testutils.ProjectControlElements(driver)
            project_control.container_status_stopped.wait(90)

            assert project_control.container_status_stopped.find().is_displayed(), "Expected stopped container status"

            logging.info(f"Featured public project {project} was imported successfully")
            side_bar_elts = testutils.SideBarElements(driver)
            side_bar_elts.projects_icon.find().click()
            time.sleep(2)
            #TODO: add graphql query to assert projects exist
    except Exception as e:
        logging.error(e)
        raise
    finally:
        # Deleting projects from gigantum directory
        for project in featured_public_projects:
            project_info = project.split('/')
            logging.info(f"Deleting project: {project_info[2]}")
            testutils.graphql_helpers.delete_local_project(project_info[1], project_info[2])


def test_import_zip_projects(driver: selenium.webdriver, *args, **kwargs):
    """
    Tests that projects can be imported via zip file
    """
    project_name = 'sample-prj'
    filepath = f"{os.environ['HOME']}/gigantum-client/resources/sample-prj-93f4b4.zip"

    # Login and remove guide
    user = testutils.log_in(driver)
    testutils.GuideElements(driver).remove_guide()
    try:
        # Importing project
        logging.info(f"Importing zip project: sample-prj-93f4b4.zip")
        import_project_elts = testutils.ImportProjectElements(driver)
        import_project_elts.import_existing_button.wait().click()
        import_project_elts.import_project_drag_and_drop(filepath)

        # Checking that the project shows up in project view
        side_bar_elts = testutils.SideBarElements(driver)
        side_bar_elts.projects_icon.find().click()
        time.sleep(2)
        title = import_project_elts.first_project_card_title.text
        assert title == project_name
        # TODO: add graph ql query to assert project exists
    except Exception as e:
        logging.error(e)
        raise
    finally:
        # Deleting project via graphql api
        logging.info(f"Deleting project: sample-prj")
        testutils.graphql_helpers.delete_local_project(user, 'sample-prj')
