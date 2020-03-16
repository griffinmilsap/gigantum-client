import logging
import os
import time
import subprocess
from subprocess import Popen, PIPE

import selenium
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.common.action_chains import ActionChains

from .testutils import load_credentials, unique_dataset_name, unique_project_description


class CssElement:
    def __init__(self, driver: selenium.webdriver, selector: str):
        self.driver = driver
        self.selector = selector

    def __call__(self):
        return self.find()

    def find(self):
        """Immediately try to find and return the element."""
        return self.driver.find_element_by_css_selector(self.selector)

    def click(self):
        """Immediately try to find and click the element."""
        return self.find().click()

    def wait_to_appear(self, nsec: int = 20):
        """Wait until the element appears."""
        t0 = time.time()
        try:
            wait = WebDriverWait(self.driver, nsec)
            wait.until(expected_conditions.visibility_of_element_located((By.CSS_SELECTOR, self.selector)))
        except Exception as e:
            tf = time.time()
            m = f'Timed out on {self.selector} after {tf-t0:.1f}sec'
            logging.error(m)
            if not str(e).strip():
                raise ValueError(m)
            else:
                raise e
        return self.find()

    def wait_to_disappear(self, nsec: int = 20):
        """Wait until the element disappears."""
        t0 = time.time()
        try:
            wait = WebDriverWait(self.driver, nsec)
            wait.until(expected_conditions.invisibility_of_element_located((By.CSS_SELECTOR, self.selector)))
        except Exception as e:
            tf = time.time()
            m = f'Timed out on {self.selector} after {tf - t0:.1f}sec'
            logging.error(m)
            if not str(e).strip():
                raise ValueError(m)
            else:
                raise e

    def selector_exists(self) -> bool:
        try:
            # This throws an exception if it fails
            self.find()
            return True  # i.e., Query succeeded
        except NoSuchElementException:
            return False


class UiComponent:
    def __init__(self, driver: selenium.webdriver):
        self.driver = driver


class Auth0LoginElements(UiComponent):
    @property
    def login_green_button(self):
        return CssElement(self.driver, ".Login__button")

    @property
    def auth0_lock_widget(self):
        return CssElement(self.driver, ".auth0-lock-form")

    @property
    def auth0_lock_button(self):
        return CssElement(self.driver, ".auth0-lock-social-button")

    @property
    def not_your_account_button(self):
        return CssElement(self.driver, ".auth0-lock-alternative-link")

    @property
    def username_input(self):
        return CssElement(self.driver, ".auth0-lock-input[name=username]")

    @property
    def password_input(self):
        return CssElement(self.driver, ".auth0-lock-input[name=password]")

    @property
    def login_grey_button(self):
        return CssElement(self.driver, ".auth0-lock-submit")

    def do_login(self, username, password):
        """Perform login."""
        self.username_input.wait_to_appear().click()
        self.username_input().send_keys(username)
        self.password_input.wait_to_appear().click()
        self.password_input().send_keys(password)
        try:
            self.login_grey_button.wait_to_appear().click()
        except:
            pass


class SideBarElements(UiComponent):
    @property
    def projects_icon(self):
        return CssElement(self.driver, ".SideBar__nav-item--labbooks")

    @property
    def datasets_icon(self):
        return CssElement(self.driver, ".SideBar__icon--datasets")

    @property
    def username_button(self):
        return CssElement(self.driver, "#username")

    @property
    def logout_button(self):
        return CssElement(self.driver, "#logout")

    def do_logout(self, username=None):
        """Perform logout."""
        logging.info(f"Logging out as {username}")
        self.username_button.wait_to_appear().click()
        self.logout_button.wait_to_appear().click()
        auth0_login_elts = Auth0LoginElements(self.driver)
        auth0_login_elts.login_green_button.wait_to_appear()


class GuideElements(UiComponent):
    @property
    def got_it_button(self):
        return CssElement(self.driver, ".button--green")

    @property
    def guide_button(self):
        return CssElement(self.driver, ".Helper-guide-slider")

    @property
    def helper_button(self):
        return CssElement(self.driver, ".Helper__button--open")

    def remove_guide(self):
        """Remove guide icons and messages."""
        try:
            logging.info("Getting rid of 'Got it!'")
            self.got_it_button.wait_to_appear().click()
            logging.info("Turning off guide and helper")
            self.guide_button.wait_to_appear().click()
            self.helper_button.wait_to_appear().click()
        except Exception as e:
            logging.warning(e)


class ImportProjectElements(UiComponent):
    @property
    def import_existing_button(self):
        return CssElement(self.driver, ".btn--import~.btn--import")

    @property
    def project_url_input(self):
        return CssElement(self.driver, ".Import__input")

    @property
    def import_project_file_area(self):
        return CssElement(self.driver, ".DropZone")

    @property
    def import_project_button(self):
        return CssElement(self.driver, ".Btn--last")

    def import_project_via_url(self, project_url):
        """Import a project via the project url."""
        _, owner, project_title = project_url.split('/')
        logging.info(f"Importing project {project_title} via url")
        self.import_existing_button.wait_to_appear().click()
        self.project_url_input.find().send_keys(project_url)
        project_control = ProjectControlElements(self.driver)
        self.import_project_button.wait_to_appear().click()
        project_control.container_status_building.wait_to_appear(20)
        project_control.container_status_stopped.wait_to_appear(500)

    def import_project_via_zip_file_drag_and_drop(self, file_path):
        """Import a project via zip file drag and drop in the zip file drop zone."""
        project_zip_file = file_path.rsplit("/", 1)[1]
        logging.info(f"Importing project {project_zip_file} via zip file drag and drop")
        self.import_existing_button.wait_to_appear().click()
        with open("testutils/file_browser_drag_drop_script.js", "r") as js_file:
            js_script = js_file.read()
        file_input = self.driver.execute_script(js_script, self.import_project_file_area.find(), 0, 0)
        file_input.send_keys(file_path)
        self.import_project_button.wait_to_appear().click()
        project_control = ProjectControlElements(self.driver)
        project_control.container_status_building.wait_to_appear(20)
        project_control.container_status_stopped.wait_to_appear(500)


class AddProjectElements(UiComponent):
    @property
    def create_new_button(self):
        return CssElement(self.driver, ".btn--import")

    @property
    def project_title_input(self):
        return CssElement(self.driver, ".CreateLabbook input")

    @property
    def project_description_input(self):
        return CssElement(self.driver, ".CreateLabbook__description-input")

    @property
    def project_continue_button(self):
        return CssElement(self.driver, ".CreateModal__buttons > .ButtonLoader")


class AddProjectBaseElements(UiComponent):
    @property
    def arrow_button(self):
        return CssElement(self.driver, ".slick-arrow slick-next")

    @property
    def create_project_button(self):
        return CssElement(self.driver, ".ButtonLoader")

    @property
    def py2_minimal_base_button(self):
        return CssElement(self.driver, "h6[data-name='python2-minimal']")

    @property
    def py3_minimal_base_button(self):
        return CssElement(self.driver, "h6[data-name='python3-minimal']")

    @property
    def py3_data_science_base_button(self):
        return CssElement(self.driver, "h6[data-name='python3-data-science']")

    @property
    def r_tidyverse_base_button(self):
        return CssElement(self.driver, "h6[data-name='r-tidyverse']")

    @property
    def rstudio_base_button(self):
        return CssElement(self.driver, "h6[data-name='rstudio-server']")


class ProjectControlElements(UiComponent):
    @property
    def start_stop_container_button(self):
        return CssElement(self.driver, ".ContainerStatus__toggle-btn")

    @property
    def container_status_stopped(self):
        return CssElement(self.driver, ".flex>.Stopped")

    @property
    def container_status_building(self):
        return CssElement(self.driver, ".flex>.Building")

    @property
    def container_status_running(self):
        return CssElement(self.driver, ".flex>.Running")

    @property
    def container_status_rebuild(self):
        return CssElement(self.driver, ".flex>.Rebuild")

    @property
    def container_status_publishing(self):
        return CssElement(self.driver, ".flex>.Publishing")

    @property
    def container_status_syncing(self):
        return CssElement(self.driver, ".flex>.Syncing")

    @property
    def footer_notification_message(self):
        return CssElement(self.driver, ".Footer__messageList")

    @property
    def close_footer_notification_button(self):
        return CssElement(self.driver, ".Footer__messageContainer > .Footer__disc-button")

    @property
    def devtool_launch_button(self):
        return CssElement(self.driver, ".DevTools__btn--launch")

    def launch_devtool(self, tool_name='dev tool'):
        """Launch a dev tool, then switch to it.
        tool_name:
            Name of the dev tool, used only for messages
        """
        logging.info(f"Switching to {tool_name}")
        self.devtool_launch_button.wait_to_appear().click()
        self.open_devtool_tab(tool_name)

    def open_devtool_tab(self, tool_name) -> None:
        """Wait for dev tool tab, then switch to it.
        tool_name:
            Name of the dev tool, used only in Exception message
        """
        # Starting a dev tool may take a long time, hence the 35 second timeout
        waiting_start = time.time()
        window_handles = self.driver.window_handles
        while len(window_handles) == 1:
            window_handles = self.driver.window_handles
            if time.time() - waiting_start > 45:
                raise ValueError(f'Timed out waiting for {tool_name} tab (35 second max)')
        self.driver.switch_to.window(window_handles[1])

    def open_gigantum_client_tab(self) -> None:
        """Switch to the Gigantum Client tab."""
        window_handles = self.driver.window_handles
        self.driver.switch_to.window(window_handles[0])


class OverviewElements(UiComponent):
    @property
    def project_description(self):
        return CssElement(self.driver, ".Description__text")


class ActivityElements(UiComponent):
    @property
    def link_activity_tab(self):
        return CssElement(self.driver, "li#activity > a")

    @property
    def first_card_label(self):
        return CssElement(self.driver, "h6.ActivityCard__commit-message")

    @property
    def first_card_img(self):
        """Returns the first img in an Activity Detail List - not necessarily from the first list!"""
        return CssElement(self.driver, "li.DetailsRecords__item img")


class EnvironmentElements(UiComponent):
    @property
    def add_packages_button(self):
        return CssElement(self.driver, ".Btn__plus--featurePosition")

    @property
    def add_packages_modal(self):
        return CssElement(self.driver, "#modal")

    @property
    def package_manager_dropdown(self):
        return CssElement(self.driver, ".Dropdown")

    @property
    def conda_package_manager_dropdown(self):
        return CssElement(self.driver, ".Dropdown__item:nth-child(2)")

    @property
    def apt_package_manager_dropdown(self):
        return CssElement(self.driver, ".Dropdown__item:nth-child(3)")

    @property
    def package_name_input(self):
        return CssElement(self.driver, ".AddPackageForm__name input")

    @property
    def specify_version_button(self):
        return CssElement(self.driver, ".Radio.flex.relative .align-self--center")

    @property
    def specify_version_textbox(self):
        return CssElement(self.driver, "input:nth-child(3)")

    @property
    def package_version_input(self):
        return CssElement(self.driver, ".PackageDependencies__input--version")

    @property
    def add_button(self):
        return CssElement(self.driver, ".Btn__add")

    @property
    def add_requirements_file_button(self):
        return CssElement(self.driver, ".AddPackages__header--file")

    @property
    def add_requirements_file_area(self):
        return CssElement(self.driver, ".Dropbox")

    @property
    def add_requirements_file_information(self):
        return CssElement(self.driver, ".Requirements__dropped-file")

    @property
    def install_packages_button(self):
        return CssElement(self.driver, ".PackageQueue__buttons > .Btn:nth-child(2)")

    @property
    def package_info_area(self):
        return CssElement(self.driver, ".PackageBody p")

    @property
    def package_info_table_version_one(self):
        return CssElement(self.driver, ".PackageRow:nth-child(1) .PackageRow__version")

    @property
    def package_info_table_version_two(self):
        return CssElement(self.driver, ".PackageRow:nth-child(2) .PackageRow__version")

    @property
    def package_info_table_version_three(self):
        return CssElement(self.driver, ".PackageRow:nth-child(3) .PackageRow__version")

    @property
    def trash_can_button(self):
        return CssElement(self.driver, ".Btn__delete-secondary")

    @property
    def check_box_button(self):
        return CssElement(self.driver, ".CheckboxMultiselect")

    @property
    def check_box_trash_can_button(self):
        return CssElement(self.driver, ".Btn__delete-white")

    @property
    def advanced_configuration_button(self):
        return CssElement(self.driver, ".Btn__advanced")

    @property
    def custom_docker_edit_button(self):
        return CssElement(self.driver, ".CustomDockerfile__content .Btn")

    @property
    def custom_docker_text_input(self):
        return CssElement(self.driver, ".CustomDockerfile__content textarea")

    @property
    def custom_docker_save_button(self):
        return CssElement(self.driver, ".CustomDockerfile__content-save-button")

    @property
    def add_sensitive_file_manager_upload(self):
        return CssElement(self.driver, "#add_secret")

    @property
    def sensitive_file_label(self):
        return CssElement(self.driver, ".AddSecret__label")

    @property
    def sensitive_file_save_button(self):
        return CssElement(self.driver, ".Btn.Btn--last")

    @property
    def sensitive_file_table(self):
        return CssElement(self.driver, ".SecretsTable__name")

    @property
    def add_sensitive_file_location(self):
        return CssElement(self.driver, ".AddSecret__input")

    def open_add_packages_modal(self, username, project_title):
        """Open Add Packages modal."""
        self.driver.get(os.environ['GIGANTUM_HOST'] + f'/projects/{username}/{project_title}/environment')
        self.driver.execute_script("window.scrollBy(0, -400);")
        self.driver.execute_script("window.scrollBy(0, 400);")
        self.add_packages_button.wait_to_appear().click()

    def specify_package_version(self, version):
        """Specify package version."""
        self.specify_version_button.click()
        self.specify_version_textbox.find().send_keys(version)

    def add_pip_package(self, pip_package, *args):
        """Add a pip package with optional pip package version."""
        logging.info(f"Adding pip package {pip_package}")
        self.package_name_input.find().send_keys(pip_package)
        try:
            self.specify_package_version(args)
        except:
            pass
        self.add_button.wait_to_appear().click()

    def add_conda_package(self, conda_package, version):
        """Add a conda package."""
        self.package_manager_dropdown.wait_to_appear().click()
        self.conda_package_manager_dropdown.wait_to_appear().click()
        logging.info(f"Adding conda package {conda_package}")
        self.package_name_input.find().send_keys(conda_package)
        self.specify_package_version(version)
        self.add_button.wait_to_appear().click()

    def add_apt_package(self, apt_package):
        """Add an apt package."""
        self.package_manager_dropdown.wait_to_appear().click()
        self.apt_package_manager_dropdown.wait_to_appear().click()
        logging.info(f"Adding apt package {apt_package}")
        self.package_name_input.find().send_keys(apt_package)
        self.add_button.wait_to_appear().click()

    def drag_drop_requirements_file_in_drop_zone(self, file_content="gigantum==0.19"):
        """Drag and drop a requirements file into the requirements file drop zone."""
        logging.info("Dragging and dropping a requirements.txt file into the drop zone")
        with open("testutils/file_browser_drag_drop_script.js", "r") as js_file:
            js_script = js_file.read()
        if os.name == 'nt':
            file_path = "C:\\tmp\\requirements.txt"
        else:
            file_path = "/tmp/requirements.txt"
        with open(file_path, "w") as example_file:
            example_file.write(file_content)
        file_input = self.driver.execute_script(js_script, self.add_requirements_file_area.find(), 0, 0)
        file_input.send_keys(file_path)
        self.add_requirements_file_information.wait_to_appear()

    def install_queued_packages(self, nsec: int = 300):
        """Install all queued packages inside the project container."""
        logging.info("Waiting for packages to validate")
        for t in range(nsec):
            try:
                if self.install_packages_button.find().is_enabled():
                    break
                else:
                    time.sleep(0.5)
            except:
                logging.error(f"Packages took longer than {t} seconds to validate")
                raise NoSuchElementException(f"Packages took longer than {t} seconds to validate")
        logging.info("Installing packages")
        self.install_packages_button.click()
        self.add_packages_modal.wait_to_disappear(nsec)
        project_control = ProjectControlElements(self.driver)
        project_control.container_status_stopped.wait_to_appear(200)

    def delete_package_via_trash_can_button(self, package):
        """Delete a package via the trash can icon."""
        logging.info(f"Deleting {package} using the trash can button")
        project_control = ProjectControlElements(self.driver)
        try:
            project_control.close_footer_notification_button.click()
        except:
            pass
        self.trash_can_button.click()
        project_control.container_status_building.wait_to_appear()
        project_control.container_status_stopped.wait_to_appear(20)

    def delete_package_via_check_box_button(self, package):
        """Delete a package via the check box and pop up trash can icon."""
        logging.info(f"Deleting {package} using the check box button")
        project_control = ProjectControlElements(self.driver)
        try:
            project_control.close_footer_notification_button.click()
        except:
            pass
        self.check_box_button.click()
        self.check_box_trash_can_button.wait_to_appear().click()
        project_control.container_status_building.wait_to_appear()
        project_control.container_status_stopped.wait_to_appear(20)

    def obtain_container_pip_packages(self, username, project_title):
        """Check which pip packages are installed inside the project container."""
        container_id = subprocess.check_output(["docker", "ps", "-aqf",
                                                f"name=gmlb-{username}-{username}-{project_title}"
                                                ]).decode('utf-8').strip()
        container_pip_packages = subprocess.check_output(["docker", "exec", container_id,
                                                          "pip", "freeze"]).decode('utf-8').strip()
        return container_pip_packages

    def add_custom_docker_instructions(self, username, project_title, docker_instruction):
        """Add a custom Docker instruction."""
        logging.info("Adding custom Docker instruction")
        self.driver.get(os.environ['GIGANTUM_HOST'] + f'/projects/{username}/{project_title}/environment')
        self.driver.execute_script("window.scrollBy(0, 600);")
        self.advanced_configuration_button.wait_to_appear().click()
        self.custom_docker_edit_button.find().click()
        self.custom_docker_text_input.wait_to_appear().send_keys(docker_instruction)
        self.driver.execute_script("window.scrollBy(0, 400);")
        self.custom_docker_save_button.wait_to_appear().click()

    def add_sensitive_file(self, username, project_title, sensitive_file_path, sensitive_file_destination):
        """Add a sensitive file."""
        logging.info("Adding sensitive file")
        self.driver.get(os.environ['GIGANTUM_HOST'] + f'/projects/{username}/{project_title}/environment')
        self.driver.execute_script("window.scrollBy(0, 600);")
        self.advanced_configuration_button.wait_to_appear().click()
        self.driver.execute_script("window.scrollBy(0, 600);")
        self.add_sensitive_file_manager_upload.find().send_keys(sensitive_file_path)
        self.add_sensitive_file_location.click()
        self.add_sensitive_file_location.find().send_keys(Keys.BACKSPACE)
        self.add_sensitive_file_location.find().send_keys(Keys.BACKSPACE)
        self.add_sensitive_file_location.find().send_keys(sensitive_file_destination)
        self.sensitive_file_save_button.click()
        self.sensitive_file_table.wait_to_appear()


class JupyterLabElements(UiComponent):
    @property
    def jupyter_notebook_button(self):
        return CssElement(self.driver, ".jp-LauncherCard-label")

    @property
    def code_input(self):
        return CssElement(self.driver, ".CodeMirror-line")

    @property
    def run_button(self):
        return CssElement(self.driver, ".jp-RunIcon")

    @property
    def code_output(self):
        return CssElement(self.driver, ".jp-OutputArea-output > pre")


class RStudioElements(UiComponent):
    @property
    def some_selected_tab(self):
        """A selector to let us wait until tabs are populated"""
        return CssElement(self.driver, ".gwt-TabLayoutPanelTab-selected")

    @property
    def selected_files_tab(self):
        """A compound selector for the *files* tab ONLY if it's selected"""
        return CssElement(self.driver, ".gwt-TabLayoutPanelTab-selected #rstudio_workbench_tab_files")

    @property
    def selected_plots_tab(self):
        """A compound selector for the *plots* tab ONLY if it's selected"""
        return CssElement(self.driver, ".gwt-TabLayoutPanelTab-selected #rstudio_workbench_tab_plots")

    @property
    def new_button(self):
        """The "New" / "+" button"""
        return CssElement(self.driver, 'div.rstheme_toolbarWrapper > table table td')

    @property
    def r_notebook(self):
        """The R Notebook button - visible only after `new_button` is clicked"""
        return CssElement(self.driver, 'table#rstudio_label_r_notebook_command')

    def new_notebook(self):
        """Create a new notebook."""
        self.new_button.click()
        self.r_notebook.wait_to_appear().click()

    def ctrl_shift_enter(self, actions):
        """Useful for executing a code block"""
        return actions.key_down(Keys.SHIFT).key_down(Keys.CONTROL).send_keys(Keys.ENTER) \
            .key_up(Keys.SHIFT).key_up(Keys.CONTROL).perform()


class FileBrowserElements(UiComponent):
    @property
    def file_browser_area(self):
        return CssElement(self.driver, ".FileBrowser")

    @property
    def file_browser_message(self):
        return CssElement(self.driver, ".Dropbox--menu")

    @property
    def input_file_browser_contents_list(self):
        # method to load the file/directory names in the input file browser for testing. Sort of a hack but it works.
        contents = self.driver.find_element_by_css_selector(".FileBrowser__body").text
        return [x for x in contents.split('\n')[0::2] if x not in ['a few seconds ago', 'a minute ago']]

    @property
    def file_information(self):
        return CssElement(self.driver, ".File__text")

    @property
    def rename_file_button(self):
        return CssElement(self.driver, ".Btn__rename")

    def rename_input_file(self, current_filename: str, suffix: str):
        # A method that adds a string to a file name in the input file browser. Sort of a hack for now but it works.
        self.driver.find_element_by_xpath(f"//input[@value='{current_filename}']").click()
        self.driver.find_element_by_xpath(f"//input[@value='{current_filename}']").send_keys(suffix)

    @property
    def confirm_file_rename_button(self):
        return CssElement(self.driver, ".justify-space-around>.File__btn--rename-add")

    @property
    def untracked_directory(self):
        return CssElement(self.driver, ".Folder__cell")

    @property
    def trash_can_button(self):
        return CssElement(self.driver, ".Btn__delete-secondary")

    @property
    def confirm_delete_file_button(self):
        return CssElement(self.driver, ".ActionsMenu__popup>.justify--space-around>.File__btn--add")

    @property
    def link_dataset_button(self):
        return CssElement(self.driver, ".Btn__FileBrowserAction--link")

    @property
    def link_dataset_modal(self):
        return CssElement(self.driver, ".LinkModal__header-text")

    @property
    def link_dataset_card_button(self):
        return CssElement(self.driver, "div[data-selenium-id='LinkCard']")

    @property
    def confirm_link_dataset_button(self):
        return CssElement(self.driver, "button[data-selenium-id='ButtonLoader']")

    @property
    def linked_dataset_card_name(self):
        return CssElement(self.driver, ".DatasetCard__name")

    def drag_drop_file_in_drop_zone(self, file_content="sample text", output_data_target=False):
        """Drag and drop a file into a file browser drop zone."""
        logging.info("Dragging and dropping a file into the drop zone")
        with open("testutils/file_browser_drag_drop_script.js", "r") as js_file:
            js_script = js_file.read()
        if os.name == 'nt':
            file_path = "C:\\tmp\\sample-upload.txt"
        else:
            file_path = "/tmp/sample-upload.txt"
        with open(file_path, "w") as example_file:
            example_file.write(file_content)
        # This deals with the untracked directory in output data
        if output_data_target:
            file_input = self.driver.execute_script(js_script, self.untracked_directory.find(), 0, 0)
        else:
            file_input = self.driver.execute_script(js_script, self.file_browser_area.find(), 0, 0)
        file_input.send_keys(file_path)
        # Time sleep consistent and necessary
        time.sleep(5)

    def link_dataset(self, dataset_title, project_title):
        """Link a dataset to a project."""
        logging.info(f"Linking the dataset {dataset_title} to project {project_title}")
        self.link_dataset_button.wait_to_appear().click()
        self.link_dataset_card_button.wait_to_appear().click()
        project_control_elts = ProjectControlElements(self.driver)
        try:
            project_control_elts.close_footer_notification_button.wait_to_appear(10).click()
        except:
            pass
        self.confirm_link_dataset_button.wait_to_appear().click()
        self.link_dataset_modal.wait_to_disappear(nsec=20)


class BranchElements(UiComponent):
    @property
    def create_branch_button(self):
        return CssElement(self.driver, ".Btn--branch--create")

    @property
    def create_branch_modal(self):
        return CssElement(self.driver, "#modal")

    @property
    def branch_name_input(self):
        return CssElement(self.driver, "#CreateBranchName")

    @property
    def create_button(self):
        return CssElement(self.driver, ".CreateBranch__buttons .ButtonLoader")

    @property
    def upper_left_branch_name(self):
        return CssElement(self.driver, ".BranchMenu__dropdown-text")

    @property
    def upper_left_branch_local_only(self):
        return CssElement(self.driver, ".BranchMenu__dropdown-btn > div[data-tooltip='Local only']")

    @property
    def upper_left_branch_drop_down_button(self):
        return CssElement(self.driver, ".BranchMenu__dropdown-btn")

    @property
    def upper_left_first_branch_button(self):
        return CssElement(self.driver, ".BranchMenu__text")

    @property
    def upper_left_switching_branch(self):
        return CssElement(self.driver, ".hidden")

    @property
    def manage_branches_button(self):
        return CssElement(self.driver, ".BranchMenu__buttons button[data-tooltip='Manage Branches']")

    @property
    def manage_branches_modal(self):
        return CssElement(self.driver, ".Branches__title")

    @property
    def manage_branches_branch_name(self):
        return CssElement(self.driver, ".Branches__branchname")

    @property
    def manage_branches_local_only(self):
        return CssElement(self.driver, ".Branches__details>div[data-tooltip='Local only']")

    @property
    def manage_branches_branch_container(self):
        return CssElement(self.driver, ".Branches__branch > .Branches__base-section > .Branches__branchname-container")

    @property
    def manage_branches_merge_branch_button(self):
        return CssElement(self.driver, ".Branches__actions-section > .Branches__btn--merge")

    @property
    def manage_branches_confirm_merge_branch_button(self):
        return CssElement(self.driver, ".Branches__Modal-confirm")

    def create_local_branch(self, branch_name):
        """Create a local branch within a project."""
        logging.info(f"Creating a new local branch {branch_name}")
        self.create_branch_button.wait_to_appear().click()
        self.branch_name_input.find().send_keys(branch_name)
        self.create_button.wait_to_appear().click()
        self.create_branch_modal.wait_to_disappear()

    def switch_to_alternate_branch(self):
        """Switch from the current branch to the alternate branch."""
        logging.info("Switching from current branch to alternate branch")
        self.upper_left_branch_drop_down_button.wait_to_appear().click()
        self.upper_left_first_branch_button.wait_to_appear().click()
        self.upper_left_switching_branch.wait_to_disappear()
        # Time sleep is consistent and necessary
        time.sleep(5)

    def merge_alternate_branch(self):
        """Merge the alternate branch into the current branch."""
        logging.info("Merging alternate branch into current branch")
        project_control= ProjectControlElements(self.driver)
        project_control.container_status_stopped.wait_to_appear(30)
        self.manage_branches_button.wait_to_appear().click()
        branch_container_hover = ActionChains(self.driver).move_to_element(self.manage_branches_branch_container.find())
        branch_container_hover.perform()
        self.manage_branches_merge_branch_button.wait_to_appear().click()
        self.manage_branches_confirm_merge_branch_button.wait_to_appear().click()
        self.manage_branches_confirm_merge_branch_button.wait_to_disappear()


class CloudProjectElements(UiComponent):
    @property
    def publish_project_button(self):
        return CssElement(self.driver, ".Btn--branch--sync--publish")

    @property
    def publish_confirm_button(self):
        return CssElement(self.driver, ".VisibilityModal__buttons > .Btn--last")

    @property
    def open_collaborators_button(self):
        return CssElement(self.driver, ".Collaborators__btn")

    @property
    def collaborator_input(self):
        return CssElement(self.driver, ".CollaboratorsModal__input--collaborators")

    @property
    def collaborator_permissions_button(self):
        return CssElement(self.driver, ".CollaboratorsModal__permissions")

    @property
    def select_write_permissions_button(self):
        return self.driver.find_element_by_xpath("//div[contains(text(), 'Write')]")

    @property
    def select_admin_permissions_button(self):
        return self.driver.find_element_by_xpath("//div[contains(text(), 'Admin')]")

    @property
    def add_collaborator_button(self):
        return CssElement(self.driver, ".ButtonLoader__collaborator")

    @property
    def close_collaborators_button(self):
        return CssElement(self.driver, ".Modal__close")

    @property
    def sync_cloud_project_button(self):
        return CssElement(self.driver, ".Btn--branch--sync")

    @property
    def delete_cloud_project_button(self):
        return CssElement(self.driver, ".Card:nth-child(1) .Btn__dashboard--delete")

    @property
    def delete_cloud_project_modal(self):
        return CssElement(self.driver, ".Modal__header")

    @property
    def delete_cloud_project_input(self):
        return CssElement(self.driver, "#deleteInput")

    @property
    def delete_cloud_project_confirm_button(self):
        return CssElement(self.driver, ".ButtonLoader")

    @property
    def cloud_tab(self):
        return CssElement(self.driver, ".Tab--cloud")

    @property
    def first_cloud_project(self):
        return CssElement(self.driver, ".RemoteLabbooks__panel-title > span > span")

    @property
    def import_first_cloud_project_button(self):
        return CssElement(self.driver, ".Card:nth-child(1) .Btn__dashboard--cloud-download")

    @property
    def project_overview_project_title(self):
        return CssElement(self.driver, ".TitleSection__namespace-title")

    @property
    def merge_conflict_modal(self):
        return CssElement(self.driver, "div[data-selenium-id='ForceSync']")

    @property
    def merge_conflict_use_mine_button(self):
        return CssElement(self.driver, ".ForceSync__buttonContainer button")

    @property
    def merge_conflict_use_theirs_button(self):
        return CssElement(self.driver, ".ForceSync__buttonContainer button:nth-of-type(2)")

    @property
    def merge_conflict_abort_button(self):
        return CssElement(self.driver, ".ForceSync__buttonContainer button:nth-of-type(3)")

    def publish_private_project(self, project_title, *args):
        """Publish a project as private."""
        logging.info(f"Publishing private project {project_title}")
        self.publish_project_button.wait_to_appear().click()
        self.publish_confirm_button.wait_to_appear().click()
        project_control = ProjectControlElements(self.driver)
        project_control.container_status_publishing.wait_to_appear(60)
        project_control.container_status_stopped.wait_to_appear(30)
        # Time sleep necessary or cloud project does not appear in cloud tab
        # Once the new cloud platform is up, this can be removed
        time.sleep(15)

    def sync_cloud_project(self, project_title):
        """Sync a published project."""
        logging.info(f"Syncing cloud project {project_title}")
        self.sync_cloud_project_button.wait_to_appear().click()
        project_control = ProjectControlElements(self.driver)
        project_control.container_status_syncing.wait_to_appear(60)
        project_control.container_status_stopped.wait_to_appear(30)

    def delete_cloud_project(self, project_title):
        """Delete a published project."""
        logging.info(f"Deleting cloud project {project_title}")
        side_bar_elts = SideBarElements(self.driver)
        side_bar_elts.projects_icon.wait_to_appear().click()
        self.cloud_tab.wait_to_appear().click()
        self.delete_cloud_project_button.wait_to_appear(30).click()
        self.delete_cloud_project_input.wait_to_appear().send_keys(project_title)
        self.delete_cloud_project_confirm_button.wait_to_appear().click()
        self.delete_cloud_project_modal.wait_to_disappear(30)

    def add_collaborator_with_permissions(self, project_title, permissions="read"):
        """Add a collaborator with specified permissions to a published project."""
        logging.info(f"Adding a collaborator to {project_title} with {permissions} permissions")
        self.open_collaborators_button.wait_to_appear().click()
        collaborator = load_credentials(user_index=1)[0].rstrip()
        self.collaborator_input.wait_to_appear().send_keys(collaborator)
        if permissions == "read":
            self.add_collaborator_button.wait_to_appear().click()
            self.add_collaborator_button.wait_to_appear()
        elif permissions == "write":
            self.collaborator_permissions_button.wait_to_appear().click()
            self.select_write_permissions_button.click()
            self.add_collaborator_button.wait_to_appear().click()
            self.add_collaborator_button.wait_to_appear()
        elif permissions == "admin":
            self.collaborator_permissions_button.wait_to_appear().click()
            self.select_admin_permissions_button.click()
            self.add_collaborator_button.wait_to_appear().click()
            self.add_collaborator_button.wait_to_appear()
        else:
            assert False, "An invalid argument was supplied for permissions in add_collaborator_with_permissions"
        self.close_collaborators_button.wait_to_appear().click()
        self.close_collaborators_button.wait_to_disappear()
        return collaborator

    def check_cloud_project_remote_git_repo(self, username, project_title):
        """Obtain information regarding a remote Git repo for a given project."""
        project_path = os.path.join(os.environ['GIGANTUM_HOME'], username, username,
                                    'labbooks', project_title)
        git_get_remote_command = Popen(['git', 'remote', 'get-url', 'origin'],
                                                    cwd=project_path, stdout=PIPE, stderr=PIPE)
        cloud_project_stdout = git_get_remote_command.stdout.readline().decode('utf-8').strip()
        cloud_project_stderr = git_get_remote_command.stderr.readline().decode('utf-8').strip()
        return cloud_project_stdout, cloud_project_stderr


class DeleteProjectElements(UiComponent):
    @property
    def actions_menu_button(self):
        return CssElement(self.driver, ".ActionsMenu > .ActionsMenu__btn")

    @property
    def delete_project_modal(self):
        return CssElement(self.driver, "#modal")

    @property
    def delete_project_button(self):
        return CssElement(self.driver, ".ActionsMenu__item--delete")

    @property
    def delete_project_input(self):
        return CssElement(self.driver, "#deleteInput")

    @property
    def confirm_delete_project_button(self):
        return CssElement(self.driver, ".DeleteLabbook .ButtonLoader")

    def delete_local_project(self, project_name):
        """Delete a local project."""
        self.actions_menu_button.click()
        self.delete_project_button.wait_to_appear().click()
        self.delete_project_input.wait_to_appear().send_keys(project_name.lstrip())
        self.confirm_delete_project_button.wait_to_appear().click()
        self.delete_project_modal.wait_to_disappear()


class DatasetElements(UiComponent):
    @property
    def datasets_header(self):
        return CssElement(self.driver, ".Datasets__panel-bar")

    @property
    def dataset_title(self):
        return CssElement(self.driver, ".TitleSection__namespace-title")

    @property
    def publish_project_linked_dataset_button(self):
        return CssElement(self.driver, ".PublishDatasetsModal__buttons button:nth-of-type(2)")

    @property
    def publish_project_linked_dataset_private_button(self):
        return CssElement(self.driver, ".Radio input[id='project_private'] + span b")

    def create_dataset(self):
        """Create a new dataset."""
        dataset_title = unique_dataset_name()
        logging.info(f"Creating a new dataset {dataset_title}")
        self.driver.get(os.environ['GIGANTUM_HOST'] + "/datasets/local")
        self.datasets_header.wait_to_appear()
        add_project_elts = AddProjectElements(self.driver)
        add_project_elts.create_new_button.click()
        add_project_elts.project_title_input.find().send_keys(dataset_title)
        add_project_elts.project_description_input.find().send_keys(unique_project_description())
        add_project_elts.project_continue_button().click()
        self.dataset_title.wait_to_appear()
        # Time sleep is consistent and necessary
        time.sleep(1)
        return dataset_title

    def publish_dataset(self, dataset_title):
        """Publish a dataset as private."""
        logging.info(f"Publishing dataset {dataset_title} to cloud")
        cloud_project_elts = CloudProjectElements(self.driver)
        cloud_project_elts.publish_project_button.wait_to_appear(nsec=20).click()
        cloud_project_elts.publish_confirm_button.wait_to_appear().click()
        project_control_elts = ProjectControlElements(self.driver)
        waiting_start = time.time()
        while "Added remote" not in project_control_elts.footer_notification_message.find().text:
            time.sleep(0.5)
            if time.time() - waiting_start > 45:
                raise ValueError(f'Timed out waiting for dataset {dataset_title} to publish')

    def publish_private_project_with_unpublished_linked_dataset(self, username, project_title, dataset_title):
        """Publish a project with an unpublished linked dataset as private."""
        cloud_project_elts = CloudProjectElements(self.driver)
        cloud_project_elts.publish_project_button.wait_to_appear(nsec=20).click()
        logging.info(f"Publishing project {project_title} with unpublished linked dataset {dataset_title} "
                     f"as private to cloud")
        time.sleep(30)
        self.publish_project_linked_dataset_button.wait_to_appear(nsec=20).click()
        self.publish_project_linked_dataset_private_button.wait_to_appear().click()
        self.driver.find_element_by_css_selector(f".Radio input[id='{username}/{dataset_title}_private'] "
                                                 f"+ span b").click()
        self.publish_project_linked_dataset_button.click()
        project_control_elts = ProjectControlElements(self.driver)
        project_control_elts.container_status_publishing.wait_to_appear(180)
        project_control_elts.container_status_stopped.wait_to_appear(180)
        # Time sleep necessary or cloud project does not appear in cloud tab
        # Once the new cloud platform is up, this can be removed
        time.sleep(15)
