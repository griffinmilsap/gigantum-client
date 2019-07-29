import time
import os

import selenium
from selenium.webdriver.common.by import By

import testutils
from testutils import graphql_helpers


def test_linked_published_dataset_then_publish(driver: selenium.webdriver, *args, **kwargs):
    """
    Test that a dataset can be created, published,
    linked to a project and published with the project.
    """
    user = testutils.log_in(driver)
    testutils.GuideElements(driver).remove_guide()
    ds_elts = testutils.DatasetElements(driver)
    # Create and publish dataset
    ds_name=ds_elts.create_dataset(testutils.unique_dataset_name())
    ds_elts.publish_dataset()
    # Create a project, link dataset, and publish project
    driver.get(os.environ['GIGANTUM_HOST'])
    r = testutils.prep_py3_minimal_base(driver, skip_login=True)
    username, project_title = r.username, r.project_name
    file_browser_elts = testutils.FileBrowserElements(driver)
    file_browser_elts.link_dataset('a', 'b')
    time.sleep(4)
    cloud_project_elts = testutils.CloudProjectElements(driver)
    cloud_project_elts.publish_private_project(project_title)
    time.sleep(4)

    # TODO - Use query to affirm that dataset linked properly

#
# def test_published_dataset_link_sync(driver: selenium.webdriver, *args, **kwargs):
#     """
#     1. create and publish a dataset
#     2. create a project and publish the project
#     3. link the dataset and sync
#
#     Args:
#         driver
#     """
#     # create a dataset
#     # dataset set up
#     testutils.log_in(driver)
#     time.sleep(2)
#     testutils.remove_guide(driver)
#     time.sleep(2)
#     # create and publish datset
#     dataset_title_local = testutils.create_dataset(driver)
#     testutils.publish_dataset(driver)
#
#     # check published dataset in the cloud
#     time.sleep(3)
#     dataset_title_cloud = driver.find_element_by_css_selector(".RemoteDatasets__panel-title:first-child span span").text
#
#     assert dataset_title_local == dataset_title_cloud, \
#         f"Expected dataset {dataset_title_local} be the first one in cloud tab"
#
#     # Project set up
#     driver.find_element_by_css_selector(".SideBar__nav-item--labbooks").click()
#     project_title_local = testutils.create_project_without_base(driver)
#     # Python 3 minimal base
#     testutils.add_py3_min_base(driver)
#     wait = WebDriverWait(driver, 200)
#     wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".flex>.Stopped")))
#     # Publish the project itself
#     testutils.publish_project(driver)
#     time.sleep(5)
#     publish_elts = testutils.PublishProjectElements(driver)
#     publish_elts.project_page_tab.click()
#     publish_elts.cloud_tab.click()
#     wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".RemoteLabbooks__panel-title")))
#
#     project_title_cloud = driver.find_element_by_css_selector(".RemoteLabbooks__panel-title:first-child span span").text
#     assert project_title_local == project_title_cloud, \
#         f"Expected project {project_title_local} to be the first project in the cloud tab"
#
#     # Link the dataset and sync
#     driver.find_element_by_xpath("//a[contains(text(), 'Projects')]").click()
#     time.sleep(3)
#     driver.find_element_by_css_selector(".LocalLabbooks__panel-title").click()
#     time.sleep(3)
#     testutils.link_dataset(driver)
#     linked_dataset_title = driver.find_element_by_css_selector(".DatasetBrowser__name").text
#     assert linked_dataset_title == dataset_title_local, \
#         f"Expected dataset {dataset_title_local} linked to project"
#     logging.info("Syncing the project")
#     driver.find_element_by_css_selector(".BranchMenu__btn--sync--upToDate").click()
#     wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".flex>.Stopped")))
#
#     # Delete project from cloud
#     testutils.delete_project_cloud(driver, project_title_local)
#     project_title_cloud = driver.find_element_by_css_selector(".RemoteLabbooks__panel-title:first-child span span").text
#     assert project_title_cloud != project_title_local, "Expected project no longer the first one in cloud tab"
#
#     # Delete dataset from cloud
#     testutils.delete_dataset_cloud(driver, dataset_title_local)
#     dataset_title_cloud = driver.find_element_by_css_selector(".RemoteDatasets__panel-title:first-child span span").text
#
#     assert dataset_title_local != dataset_title_cloud, \
#         f"Expected dataset {dataset_title_local} no longer the first one in cloud tab"
#
#
# def test_unpublished_dataset_link(driver: selenium.webdriver, *args, **kwargs):
#     """
#     1. create a dataset, don't publish
#     2. create a project and link the dataset
#     3. publish the project (dataset is published along with project)
#
#     Args:
#         driver
#     """
#     # create a dataset
#     # dataset set up
#     testutils.log_in(driver)
#     time.sleep(2)
#     testutils.remove_guide(driver)
#     time.sleep(2)
#     # create and publish datset
#     dataset_title_local = testutils.create_dataset(driver)
#
#     # Project set up
#     driver.find_element_by_css_selector(".SideBar__nav-item--labbooks").click()
#     project_title_local = testutils.create_project_without_base(driver)
#     # Python 3 minimal base
#     testutils.add_py3_min_base(driver)
#     wait = WebDriverWait(driver, 200)
#     wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".flex>.Stopped")))
#
#     # Link the dataset
#     testutils.link_dataset(driver)
#     linked_dataset_title = driver.find_element_by_css_selector(".DatasetBrowser__name").text
#
#     assert linked_dataset_title == dataset_title_local, \
#         f"Expected dataset {dataset_title_local} linked to project"
#
#     # Publish the project with dataset linked
#     logging.info("Publishing project with local dataset")
#     publish_elts = testutils.PublishProjectElements(driver)
#     publish_elts.publish_project_button.click()
#     publish_elts.publish_continue_button.click()
#     time.sleep(3)
#     publish_elts.publish_private_project_button.click()
#     publish_elts.publish_private_dataset_button.click()
#     publish_elts.publish_all_button.click()
#     wait.until(EC.invisibility_of_element_located((By.CSS_SELECTOR, ".PublishDatasetsModal")))
#     wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".flex>.Stopped")))
#     time.sleep(5)
#     side_bar_elts = testutils.SideBarElements(driver)
#     side_bar_elts.projects_icon.click()
#     publish_elts.cloud_tab.click()
#     wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".RemoteLabbooks__panel-title")))
#
#     project_title_cloud = driver.find_element_by_css_selector(".RemoteLabbooks__panel-title:first-child span span").text
#     assert project_title_local == project_title_cloud, \
#         f"Expected project {project_title_local} to be the first project in the cloud tab"
#
#     # Delete project from cloud
#     testutils.delete_project_cloud(driver, project_title_local)
#     project_title_cloud = driver.find_element_by_css_selector(".RemoteLabbooks__panel-title:first-child span span").text
#     assert project_title_cloud != project_title_local, \
#         f"Expected project {project_title_local} no longer the first one in cloud tab"
#
#     # Delete dataset from cloud
#     testutils.delete_dataset_cloud(driver, dataset_title_local)
#     dataset_title_cloud = driver.find_element_by_css_selector(".RemoteDatasets__panel-title:first-child span span").text
#
#     assert dataset_title_local != dataset_title_cloud, \
#         f"Expected dataset {dataset_title_local} no longer the first one in cloud tab"
#
#
#
#
#
#
