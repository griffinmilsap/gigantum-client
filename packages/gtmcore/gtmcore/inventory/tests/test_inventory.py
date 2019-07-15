from gtmcore.inventory.inventory import InventoryManager
from gtmcore.fixtures import mock_config_file


class TestInventory(object):
    def test_repository_exists_no_repo(self, mock_config_file):
        inv_manager = InventoryManager(mock_config_file[0])
        inv_manager.create_labbook("test", "test", "labbook1", description="my first labbook")
        assert inv_manager.repository_exists('test', 'test', 'does-not-exist') is False

    def test_repository_exists_project(self, mock_config_file):
        inv_manager = InventoryManager(mock_config_file[0])
        inv_manager.create_labbook("test", "test", "labbook1", description="my first labbook")
        assert inv_manager.repository_exists('test', 'test', 'labbook1') is True

    def test_repository_exists_dataset(self, mock_config_file):
        inv_manager = InventoryManager(mock_config_file[0])
        inv_manager.create_dataset("test", "test", "dataset-1", storage_type='gigantum_object_v1')
        assert inv_manager.repository_exists('test', 'test', 'labbook1') is False
        assert inv_manager.repository_exists('test', 'test', 'dataset-1') is True
