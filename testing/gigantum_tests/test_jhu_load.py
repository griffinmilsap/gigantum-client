import logging
import time

import selenium
from selenium.webdriver.common.action_chains import ActionChains

import testutils
from testutils import CssElement
from testutils.graphql_helpers import delete_local_project


# Currently we skip this test
def __test_jhu_neurodata_import(driver: selenium.webdriver, *args, **kwargs):
    """
    Test that featured public projects import and build successfully.
    """

    user = testutils.log_in(driver)
    testutils.GuideElements(driver).remove_guide()

    project = "gigantum.com/neurodata/rerf"
    _, owner, project_name = project.split('/')
    logging.info(f"Importing featured public project: {project_name}")
    try:
        import_project_elts = testutils.ImportProjectElements(driver)
        import_project_elts.import_project_via_url(project)
        project_control = testutils.ProjectControlElements(driver)
        project_control.container_status_stopped.wait_to_appear(600)
        assert project_control.container_status_stopped.find().is_displayed(), "Expected stopped container status"
        logging.info(f"Featured public project {project} was imported successfully")

        # Open JupyterLab and create Jupyter notebook
        project_control = testutils.ProjectControlElements(driver)
        project_control.container_status_stopped.wait_to_appear(150)
        project_control.launch_devtool('JupyterLab')
        time.sleep(5)
        nb = CssElement(driver, 'li[title="plot_emsemble_oob.ipynb"]').find()
        ac = ActionChains(driver)
        ac.double_click(nb).perform()

        # Running all cells
        jl_control = testutils.JupyterLabElements(driver)
        jl_control.run_button.wait_to_appear().click()
        jl_control.run_button.wait_to_appear().click()
        jl_control.run_button.wait_to_appear().click()
        jl_control.run_button.wait_to_appear().click()
        jl_control.run_button.wait_to_appear().click()
        logging.info('Getting jupyterlab status')
        status = driver.find_element_by_xpath('//*[@title="Active kernel type for plot_emsemble_oob.ipynb"]')
        time.sleep(1)

        # Waiting until all cells have finished running
        timeout = 60
        while "Busy" in status.text:
            if timeout < 0:
                break
            logging.info('Kernel still running')
            time.sleep(1)
            timeout -= 1

        # Checking kernel actually finished running
        assert "Idle" in status.text, "Expected Kernel to stop running"
        logging.info('Kernel done running')

    finally:
        try:
            _, owner, project_name = project.split('/')
            delete_local_project(owner, project_name)
        except Exception as e:
            logging.error(f'Failed to delete project {owner}/{project_name}: {e}')
