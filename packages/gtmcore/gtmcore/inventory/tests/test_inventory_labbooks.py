import pytest
import os
import shutil
import yaml
import time

from gtmcore.labbook import LabBook
from gtmcore.inventory.inventory import InventoryManager, InventoryException
from gtmcore.gitlib.git import GitAuthor

from gtmcore.fixtures import mock_config_file


class TestInventoryLabbooks(object):
    def test_uses_config(self, mock_config_file):
        i = InventoryManager(mock_config_file[0])
        assert i.inventory_root == mock_config_file[1]

    def test_list_labbooks_empty(self, mock_config_file):
        i = InventoryManager(mock_config_file[0])
        assert len(i.list_repository_ids(username="none", repository_type="labbook")) == 0

    def test_list_labbooks_wrong_base_dir(self, mock_config_file):
        i = InventoryManager(mock_config_file[0])
        assert i.list_repository_ids(username="not-a-user", repository_type="labbook") == []

    def test_list_labbooks_full_set(self, mock_config_file):
        ut_username = "ut-owner-1"
        owners = [f"ut-owner-{i}" for i in range(4)]
        lbnames = [f'unittest-labbook-{i}' for i in range(6)]
        created_lbs = []
        inv_manager = InventoryManager(mock_config_file[0])
        for ow in owners:
            for lbname in lbnames:
                l = inv_manager.create_labbook(ut_username, ow, lbname)
                created_lbs.append(l)

        get_owner = lambda x: InventoryManager(mock_config_file[0]).query_owner(x)
        condensed_lbs = [(ut_username, get_owner(l), l.name) for l in created_lbs]
        inv_manager = InventoryManager(mock_config_file[0])
        t0 = time.time()
        result_under_test = inv_manager.list_repository_ids(username=ut_username, repository_type="labbook")
        assert time.time() - t0 < 1.0, "list_repository_ids should return in under 1 second"
        assert len(list(set(condensed_lbs))) == 6 * 4
        assert len(list(set(result_under_test))) == 6 * 4
        for r in result_under_test:
            assert r in condensed_lbs

    def test_list_labbooks_az(self, mock_config_file):
        """Test list az labbooks"""
        inv_manager = InventoryManager(mock_config_file[0])
        lb1 = inv_manager.create_labbook("user1", "user1", "labbook0", description="my first labbook")
        lb2 = inv_manager.create_labbook("user1", "user1", "labbook12", description="my second labbook")
        lb3 = inv_manager.create_labbook("user1", "user2", "labbook3", description="my other labbook")
        lb4 = inv_manager.create_labbook("user2", "user1", "labbook4", description="my other labbook")

        labbooks = inv_manager.list_labbooks(username="user1")
        assert len(labbooks) == 3
        assert labbooks[0].name == 'labbook0'
        assert labbooks[1].name == 'labbook3'
        assert labbooks[2].name == 'labbook12'

    def test_list_labbooks_create_date(self, mock_config_file):
        """Test list create dated sorted labbooks"""
        inv_manager = InventoryManager(mock_config_file[0])
        lb1 = inv_manager.create_labbook("user1", "user1", "labbook3", description="my first labbook")
        time.sleep(1.5)
        lb2 = inv_manager.create_labbook("user1", "user1", "asdf", description="my second labbook")
        time.sleep(1.5)
        lb3 = inv_manager.create_labbook("user1", "user2", "labbook1", description="my other labbook")

        labbooks = inv_manager.list_labbooks(username="user1", sort_mode="created_on")
        assert len(labbooks) == 3
        assert labbooks[0].name == 'labbook3'
        assert labbooks[1].name == 'asdf'
        assert labbooks[2].name == 'labbook1'

    def test_list_labbooks_create_date_no_metadata(self, mock_config_file):
        """Test list create dated sorted labbooks"""
        inv_manager = InventoryManager(mock_config_file[0])
        lb1 = inv_manager.create_labbook("user1", "user1", "labbook3", description="my first labbook")
        time.sleep(1.1)
        lb2 = inv_manager.create_labbook("user1", "user1", "asdf", description="my second labbook")
        time.sleep(1.1)
        lb3 = inv_manager.create_labbook("user1", "user2", "labbook1", description="my other labbook")
        time.sleep(1.1)
        labbooks = inv_manager.list_labbooks(username="user1", sort_mode="created_on")

        assert len(labbooks) == 3
        assert labbooks[0].name == 'labbook3'
        assert labbooks[1].name == 'asdf'
        assert labbooks[2].name == 'labbook1'

        labbooks2 = inv_manager.list_labbooks(username="user1", sort_mode="created_on")

        assert len(labbooks2) == 3
        assert labbooks2[0].name == 'labbook3'
        assert labbooks2[1].name == 'asdf'
        assert labbooks2[2].name == 'labbook1'

        os.remove(os.path.join(lb2.root_dir, '.gigantum', 'project.yaml'))
        labbooks3 = inv_manager.list_labbooks(username="user1", sort_mode='modified_on')
        assert len(labbooks3) == 2

    def test_list_labbooks_modified_date(self, mock_config_file):
        """Test list modified dated sorted labbooks"""
        inv_manager = InventoryManager(mock_config_file[0])

        lb1 = inv_manager.create_labbook("user1", "user1", "labbook3", description="my first labbook")
        time.sleep(1.2)
        lb2 = inv_manager.create_labbook("user1", "user1", "asdf", description="my second labbook")
        time.sleep(1.2)
        lb3 = inv_manager.create_labbook("user1", "user2", "labbook1", description="my other labbook")
        time.sleep(1.2)
        lb4 = inv_manager.create_labbook("user1", "user1", "hhghg", description="my other labbook")

        inv_manager = InventoryManager(mock_config_file[0])
        labbooks = inv_manager.list_labbooks(username="user1", sort_mode="modified_on")

        assert len(labbooks) == 4
        assert labbooks[0].name == 'labbook3'
        assert labbooks[1].name == 'asdf'
        assert labbooks[2].name == 'labbook1'
        assert labbooks[3].name == 'hhghg'

        # modify a repo
        time.sleep(1.2)
        with open(os.path.join(lb2.root_dir, "code", "test.txt"), 'wt') as tf:
            tf.write("asdfasdf")

        lb2.git.add_all()
        lb2.git.commit("Changing the repo")

        labbooks = inv_manager.list_labbooks(username="user1", sort_mode="modified_on")

        assert len(labbooks) == 4
        assert labbooks[0].name == 'labbook3'
        assert labbooks[1].name == 'labbook1'
        assert labbooks[2].name == 'hhghg'
        assert labbooks[3].name == 'asdf'

    def test_load_labbook_from_directory(self, mock_config_file):
        """Test loading a labbook from a directory"""
        inv_manager = InventoryManager(mock_config_file[0])
        lb = inv_manager.create_labbook("test", "test", "labbook1", description="my first labbook")
        labbook_dir = lb.root_dir
        assert labbook_dir == os.path.join(mock_config_file[1], "test", "test", "labbooks", "labbook1")
        assert type(lb) == LabBook

        # Validate directory structure
        assert os.path.isdir(os.path.join(labbook_dir, "code")) is True
        assert os.path.isdir(os.path.join(labbook_dir, "input")) is True
        assert os.path.isdir(os.path.join(labbook_dir, "output")) is True
        assert os.path.isdir(os.path.join(labbook_dir, ".gigantum")) is True
        assert os.path.isdir(os.path.join(labbook_dir, ".gigantum", "env")) is True
        assert os.path.isdir(os.path.join(labbook_dir, ".gigantum", "activity")) is True
        assert os.path.isdir(os.path.join(labbook_dir, ".gigantum", "activity", "log")) is True
        assert os.path.isdir(os.path.join(labbook_dir, ".gigantum", "activity", "index")) is True

        # Validate labbook data file
        with open(os.path.join(labbook_dir, ".gigantum", "project.yaml"), "rt") as data_file:
            data = yaml.safe_load(data_file)

        assert data["name"] == "labbook1"
        assert data["description"] == "my first labbook"
        assert "id" in data

        lb_loaded = InventoryManager(mock_config_file[0]).load_labbook_from_directory(labbook_dir)

        assert lb_loaded.root_dir == os.path.join(mock_config_file[1], "test", "test", "labbooks", "labbook1")
        assert type(lb) == LabBook

        # Validate labbook data file
        assert lb_loaded.root_dir == lb.root_dir
        assert lb_loaded.id == lb.id
        assert lb_loaded.name == lb.name
        assert lb_loaded.description == lb.description

    def test_load_labbook(self, mock_config_file):
        """Test loading a labbook from a directory"""
        inv_manager = InventoryManager(mock_config_file[0])
        lb = inv_manager.create_labbook("test", "test", "labbook1", description="my first labbook")
        labbook_dir = lb.root_dir

        assert labbook_dir == os.path.join(mock_config_file[1], "test", "test", "labbooks", "labbook1")
        assert type(lb) == LabBook

        # Validate directory structure
        assert os.path.isdir(os.path.join(labbook_dir, "code")) is True
        assert os.path.isdir(os.path.join(labbook_dir, "input")) is True
        assert os.path.isdir(os.path.join(labbook_dir, "output")) is True
        assert os.path.isdir(os.path.join(labbook_dir, ".gigantum")) is True
        assert os.path.isdir(os.path.join(labbook_dir, ".gigantum", "env")) is True
        assert os.path.isdir(os.path.join(labbook_dir, ".gigantum", "activity")) is True
        assert os.path.isdir(os.path.join(labbook_dir, ".gigantum", "activity", "log")) is True
        assert os.path.isdir(os.path.join(labbook_dir, ".gigantum", "activity", "index")) is True

        # Validate labbook data file
        with open(os.path.join(labbook_dir, ".gigantum", "project.yaml"), "rt") as data_file:
            data = yaml.safe_load(data_file)

        assert data["name"] == "labbook1"
        assert data["description"] == "my first labbook"
        assert "id" in data

        lb_loaded = inv_manager.load_labbook("test", "test", "labbook1")

        assert lb_loaded.root_dir == os.path.join(mock_config_file[1], "test",
                                                  "test", "labbooks", "labbook1")
        assert type(lb) == LabBook

        # Validate labbook data file
        assert lb_loaded.root_dir == lb.root_dir
        assert lb_loaded.id == lb.id
        assert lb_loaded.name == lb.name
        assert lb_loaded.description == lb.description
        assert lb_loaded.key == 'test|test|labbook1'

    def test_query_owner(self, mock_config_file):
        inv_manager = InventoryManager(mock_config_file[0])
        lb = inv_manager.create_labbook("test", "test", "labbook1", description="my first labbook")
        assert "test" == inv_manager.query_owner(lb)

    def test_query_owner_fail(self, mock_config_file):
        inv_manager = InventoryManager(mock_config_file[0])
        lb = inv_manager.create_labbook("test", "test", "labbook1", description="my first labbook")
        new_location = shutil.move(lb.root_dir, '/tmp')
        try:
            lb = inv_manager.load_labbook_from_directory(new_location)
            with pytest.raises(InventoryException):
                inv_manager.query_owner(lb)
        finally:
            shutil.rmtree(new_location)

    def test_delete_labbook_no_linked_datasets(self, mock_config_file):
        """Test trying to create a labbook with a name that already exists locally"""
        inv_manager = InventoryManager(mock_config_file[0])
        inv_manager.create_labbook("test", "test", "labbook1", description="my first labbook")
        inv_manager.load_labbook("test", "test", "labbook1")

        dataset_delete_jobs = inv_manager.delete_labbook("test", "test", "labbook1")
        assert dataset_delete_jobs == []

        with pytest.raises(InventoryException):
            inv_manager.load_labbook("test", "test", "labbook1")

    def test_delete_labbook_linked_dataset(self, mock_config_file):
        """Test trying to create a labbook with a name that already exists locally"""
        inv_manager = InventoryManager(mock_config_file[0])
        inv_manager.create_labbook("test", "test", "labbook1", description="my first labbook")
        lb = inv_manager.load_labbook("test", "test", "labbook1")

        auth = GitAuthor(name="test", email="user1@test.com")
        ds = inv_manager.create_dataset("test", "test", "dataset1", "gigantum_object_v1",
                                        description="my first dataset",
                                        author=auth)

        inv_manager.link_dataset_to_labbook(f"{ds.root_dir}/.git", "test", "dataset1", lb)

        dataset_delete_jobs = inv_manager.delete_labbook("test", "test", "labbook1")
        assert len(dataset_delete_jobs) == 1
        assert dataset_delete_jobs[0].namespace == "test"
        assert dataset_delete_jobs[0].name == "dataset1"

        with pytest.raises(InventoryException):
            inv_manager.load_labbook("test", "test", "labbook1")


class TestCreateLabbooks(object):

    def test_create_labbook_with_author(self, mock_config_file):
        """Test creating an empty labbook with the author set"""
        inv_manager = InventoryManager(mock_config_file[0])
        auth =  GitAuthor(name="username", email="user1@test.com")
        lb = inv_manager.create_labbook("test", "test", "labbook1",
                                                 description="my first labbook",
                                                 author=auth)
        labbook_dir = lb.root_dir
        log_data = lb.git.log()
        assert log_data[0]['author']['name'] == "username"
        assert log_data[0]['author']['email'] == "user1@test.com"
        assert log_data[0]['committer']['name'] == "Gigantum AutoCommit"
        assert log_data[0]['committer']['email'] == "noreply@gigantum.io"

    def test_create_labbook(self, mock_config_file):
        """Test creating an empty labbook"""
        inv_manager = InventoryManager(mock_config_file[0])
        lb = inv_manager.create_labbook("test", "test", "labbook1",
                                                 description="my first labbook")
        labbook_dir = lb.root_dir

        assert labbook_dir == os.path.join(mock_config_file[1], "test", "test", "labbooks", "labbook1")
        assert type(lb) == LabBook

        # Validate directory structure
        assert os.path.isdir(os.path.join(labbook_dir, "code")) is True
        assert os.path.isdir(os.path.join(labbook_dir, "input")) is True
        assert os.path.isdir(os.path.join(labbook_dir, "output")) is True
        assert os.path.isdir(os.path.join(labbook_dir, ".gigantum")) is True
        assert os.path.isdir(os.path.join(labbook_dir, ".gigantum", "env")) is True
        assert os.path.isdir(os.path.join(labbook_dir, ".gigantum", "activity")) is True
        assert os.path.isdir(os.path.join(labbook_dir, ".gigantum", "activity", "log")) is True
        assert os.path.isdir(os.path.join(labbook_dir, ".gigantum", "activity", "index")) is True

        # Validate labbook data file
        with open(os.path.join(labbook_dir, ".gigantum", "project.yaml"), "rt") as data_file:
            data = yaml.safe_load(data_file)

        assert data["name"] == "labbook1"
        assert data["description"] == "my first labbook"
        assert "id" in data

        assert lb.build_details is not None
        assert lb.creation_date is not None
        lb._validate_gigantum_data()

    def test_create_labbook_that_exists(self, mock_config_file):
        """Test trying to create a labbook with a name that already exists locally"""
        inv_manager = InventoryManager(mock_config_file[0])
        inv_manager.create_labbook("test", "test", "labbook1", description="my first labbook")
        with pytest.raises(ValueError):
            inv_manager.create_labbook("test", "test", "labbook1",
                                       description="my first labbook")
