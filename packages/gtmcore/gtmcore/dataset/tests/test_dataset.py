import time
import datetime
import os
import pytest

from gtmcore.fixtures import mock_config_file

from gtmcore.dataset.dataset import Dataset

from gtmcore.inventory.inventory import InventoryManager
from gtmcore.gitlib.git import GitAuthor


def helper_modify_dataset(dataset: Dataset):
    with open(os.path.join(dataset.root_dir, '.gigantum', 'dummy.txt'), 'wt') as testfile:
        testfile.write("asdfasdf")

    dataset.git.add_all()
    dataset.git.commit("testing")


class TestDataset(object):
    def test_is_dataset_is_managed(self, mock_config_file):
        """Test getting the create date, both when stored in the buildinfo file and when using git fallback"""
        im = InventoryManager(mock_config_file[0])
        ds = im.create_dataset("test", "test", "dataset1", "gigantum_object_v1",
                               description="my first dataset",
                               author=GitAuthor(name="test", email="test@test.com"))

        assert ds.is_managed() is True

    def test_is_dataset_create_date(self, mock_config_file):
        """Test getting the create date, both when stored in the buildinfo file and when using git fallback"""
        im = InventoryManager(mock_config_file[0])
        ds = im.create_dataset("test", "test", "dataset1", "gigantum_object_v1",
                               description="my first dataset",
                               author=GitAuthor(name="test", email="test@test.com"))

        create_on = ds.creation_date

        assert create_on.microsecond == 0
        assert create_on.tzname() == "UTC"

        assert (datetime.datetime.now(datetime.timezone.utc) - create_on).total_seconds() < 5

    def test_is_dataset_modified_date(self, mock_config_file):
        """Test getting the modified date"""
        im = InventoryManager(mock_config_file[0])
        ds = im.create_dataset("test", "test", "dataset1", "gigantum_object_v1",
                               description="my first dataset",
                               author=GitAuthor(name="test", email="test@test.com"))

        modified_1 = ds.modified_on

        time.sleep(3)
        helper_modify_dataset(ds)

        modified_2 = ds.modified_on

        assert modified_2 > modified_1

        assert modified_1.microsecond == 0
        assert modified_1.tzname() == "UTC"
        assert modified_2.microsecond == 0
        assert modified_2.tzname() == "UTC"

        assert (datetime.datetime.now(datetime.timezone.utc) - modified_1).total_seconds() < 10
        assert (datetime.datetime.now(datetime.timezone.utc) - modified_2).total_seconds() < 10

    def test_linked_to(self, mock_config_file):
        im = InventoryManager(mock_config_file[0])
        lb = im.create_labbook("test", "test", "lb1", "testing")
        ds = im.create_dataset("test", "test", "dataset1", "gigantum_object_v1",
                               description="my first dataset",
                               author=GitAuthor(name="test", email="test@test.com"))

        assert ds.linked_to() is None

        im.link_dataset_to_labbook(f"{ds.root_dir}/.git", "test", "dataset1", lb, "test")

        assert ds.linked_to() is None

        linked_datasets = im.get_linked_datasets(lb)
        assert len(linked_datasets) == 1
        assert linked_datasets[0].linked_to() == "test|test|lb1"
