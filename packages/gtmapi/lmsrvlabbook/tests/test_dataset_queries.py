import os
import aniso8601
import time
import datetime
from snapshottest import snapshot

from lmsrvcore.caching import DatasetCacheController
from lmsrvlabbook.tests.fixtures import fixture_working_dir_dataset_populated_scoped, fixture_working_dir

from gtmcore.inventory.inventory import InventoryManager
from gtmcore.gitlib.git import GitAuthor


class TestDatasetQueries(object):

    def test_get_dataset(self, fixture_working_dir_dataset_populated_scoped):
        query = """{
                    dataset(name: "dataset8", owner: "default") {
                      id
                      name
                      description
                      schemaVersion
                      datasetType{
                        name
                        id
                        description
                      }
                      visibility
                      defaultRemote
                    }
                    }
                """
        r = fixture_working_dir_dataset_populated_scoped[2].execute(query)
        assert r['data']['dataset']['description'] == 'Cats 8'
        assert r['data']['dataset']['datasetType']['description'] == "Dataset storage provided by your Gigantum account supporting files up to 5GB in size"
        assert r['data']['dataset']['datasetType']['name'] == 'Gigantum Cloud'
        assert r['data']['dataset']['name'] == 'dataset8'
        assert r['data']['dataset']['schemaVersion'] == 2
        assert r['data']['dataset']['visibility'] == "local"
        assert r['data']['dataset']['defaultRemote'] is None

    def test_get_dataset_all_fields(self, fixture_working_dir_dataset_populated_scoped, snapshot):
        query = """{
                    dataset(name: "dataset8", owner: "default") {
                      id
                      name
                      description
                      schemaVersion
                      activityRecords{
                        edges{
                            node{
                                message
                                type
                                show
                                importance
                                tags
                                }
                            }                    
                        pageInfo{
                            hasNextPage
                            hasPreviousPage
                        }
                      }
                      datasetType{
                        name
                        id
                        description
                        storageType
                        readme
                        tags
                        icon
                      }
                    }
                    }
                """
        snapshot.assert_match(fixture_working_dir_dataset_populated_scoped[2].execute(query))

        query = """{
                    dataset(name: "dataset8", owner: "default") {
                      name
                      createdOnUtc
                      modifiedOnUtc
                      
                    }
                    }
                """
        result = fixture_working_dir_dataset_populated_scoped[2].execute(query)
        assert isinstance(result['data']['dataset']['createdOnUtc'], str) is True
        assert isinstance(result['data']['dataset']['modifiedOnUtc'], str) is True
        assert len(result['data']['dataset']['createdOnUtc']) > 10
        assert len(result['data']['dataset']['modifiedOnUtc']) > 10

    def test_pagination_noargs(self, fixture_working_dir_dataset_populated_scoped, snapshot):
        query = """
                {
                datasetList{
                    localDatasets {
                        edges {
                            node {
                                name
                                description
                            }
                            cursor
                        }
                        pageInfo {
                            hasNextPage
                            hasPreviousPage
                        }
                    }
                }
                }
                """
        snapshot.assert_match(fixture_working_dir_dataset_populated_scoped[2].execute(query))

    def test_pagination_sort_az_reverse(self, fixture_working_dir_dataset_populated_scoped, snapshot):
        query = """
                {
                datasetList{
                    localDatasets(orderBy: "name", sort: "desc") {
                        edges {
                            node {
                                id
                                name
                                description
                                datasetType{
                                  storageType
                                  name
                                  description
                                }
                            }
                            cursor
                        }
                        pageInfo {
                            hasNextPage
                            hasPreviousPage
                        }
                    }
                }
                }
                """
        snapshot.assert_match(fixture_working_dir_dataset_populated_scoped[2].execute(query))

    def test_pagination_sort_create(self, fixture_working_dir_dataset_populated_scoped, snapshot):
        query = """
                {
                datasetList{
                    localDatasets(orderBy: "created_on") {
                        edges {
                            node {
                                id
                                name
                                description
                            }
                            cursor
                        }
                        pageInfo {
                            hasNextPage
                            hasPreviousPage
                        }
                    }
                }
                }
                """
        snapshot.assert_match(fixture_working_dir_dataset_populated_scoped[2].execute(query))

    def test_pagination_sort_create_desc(self, fixture_working_dir_dataset_populated_scoped, snapshot):
        query = """
                {
                datasetList{
                    localDatasets(orderBy: "created_on", sort: "desc") {
                        edges {
                            node {
                                id
                                name
                                description
                            }
                            cursor
                        }
                        pageInfo {
                            hasNextPage
                            hasPreviousPage
                        }
                    }
                }
                }
                """
        snapshot.assert_match(fixture_working_dir_dataset_populated_scoped[2].execute(query))

    def test_pagination_sort_modified(self, fixture_working_dir_dataset_populated_scoped, snapshot):

        query = """
                {
                datasetList{
                    localDatasets(orderBy: "modified_on", sort: "desc") {
                        edges {
                            node {
                                id
                                name
                                description
                            }
                            cursor
                        }
                        pageInfo {
                            hasNextPage
                            hasPreviousPage
                        }
                    }
                }
                }
                """
        snapshot.assert_match(fixture_working_dir_dataset_populated_scoped[2].execute(query))

        im = InventoryManager(fixture_working_dir_dataset_populated_scoped[0])
        ds = im.load_dataset("default", "default", "dataset4")
        with open(os.path.join(ds.root_dir, "test.txt"), 'wt') as tf:
            tf.write("asdfasdf")
        ds.git.add_all()
        ds.git.commit("Changing the repo")

        DatasetCacheController.build().clear_all()

        # Run query again
        snapshot.assert_match(fixture_working_dir_dataset_populated_scoped[2].execute(query))

    def test_pagination(self, fixture_working_dir_dataset_populated_scoped, snapshot):
        """Test pagination and cursors"""
        query = """
                {
                datasetList{
                    localDatasets(first: 2) {
                        edges {
                            node {
                                name
                                description
                            }
                            cursor
                        }
                        pageInfo {
                            hasNextPage
                            hasPreviousPage
                        }
                    }
                }
                }
                """
        snapshot.assert_match(fixture_working_dir_dataset_populated_scoped[2].execute(query))

        query = """
                {
                datasetList{
                    localDatasets(first: 5, after: "MQ==") {
                        edges {
                            node {
                                name
                                description
                            }
                            cursor
                        }
                        pageInfo {
                            hasNextPage
                            hasPreviousPage
                        }
                    }
                }
                }
                """
        snapshot.assert_match(fixture_working_dir_dataset_populated_scoped[2].execute(query))

        query = """
                {
                datasetList{
                    localDatasets(first: 3, after: "Ng==") {
                        edges {
                            node {
                                name
                                description
                            }
                            cursor
                        }
                        pageInfo {
                            hasNextPage
                            hasPreviousPage
                        }
                    }
                }
                }
                """
        snapshot.assert_match(fixture_working_dir_dataset_populated_scoped[2].execute(query))

        query = """
                {
                datasetList{
                    localDatasets(first: 3, after: "OQ==") {
                        edges {
                            node {
                                name
                                description
                            }
                            cursor
                        }
                        pageInfo {
                            hasNextPage
                            hasPreviousPage
                        }
                    }
                }
                }
                """
        snapshot.assert_match(fixture_working_dir_dataset_populated_scoped[2].execute(query))

    def test_get_dataset_create_date(self, fixture_working_dir_dataset_populated_scoped):
        """Test getting a dataset's create date"""
        im = InventoryManager(fixture_working_dir_dataset_populated_scoped[0])
        ds = im.create_dataset("default", "default", "create-on-test-ds", "gigantum_object_v1",
                               description="my first dataset",
                               author=GitAuthor(name="default", email="test@test.com"))

        query = """
        {
          dataset(name: "create-on-test-ds", owner: "default") {
            createdOnUtc
          }
        }
        """
        r = fixture_working_dir_dataset_populated_scoped[2].execute(query)
        assert 'errors' not in r
        d = r['data']['dataset']['createdOnUtc']

        # using aniso8601 to parse because built-in datetime doesn't parse the UTC offset properly (configured for js)
        create_on = aniso8601.parse_datetime(d)
        assert create_on.microsecond == 0
        assert create_on.tzname() == "+00:00"

        assert (datetime.datetime.now(datetime.timezone.utc) - create_on).total_seconds() < 5

    def test_get_dataset_modified_on(self, fixture_working_dir_dataset_populated_scoped):
        """Test getting a dataset's modified date"""
        im = InventoryManager(fixture_working_dir_dataset_populated_scoped[0])
        ds = im.create_dataset("default", "default", "modified-on-test-ds", "gigantum_object_v1",
                               description="my first dataset",
                               author=GitAuthor(name="default", email="test@test.com"))

        modified_query = """
                            {
                              dataset(name: "modified-on-test-ds", owner: "default") {
                                modifiedOnUtc
                              }
                            }
                            """
        r = fixture_working_dir_dataset_populated_scoped[2].execute(modified_query)
        assert 'errors' not in r
        d = r['data']['dataset']['modifiedOnUtc']
        # using aniso8601 to parse because built-in datetime doesn't parse the UTC offset properly (configured for js)
        modified_on_1 = aniso8601.parse_datetime(d)
        assert modified_on_1.microsecond == 0
        assert modified_on_1.tzname() == "+00:00"

        time.sleep(3)
        with open(os.path.join(ds.root_dir, '.gigantum', 'dummy.txt'), 'wt') as testfile:
            testfile.write("asdfasdf")

        ds.git.add_all()
        ds.git.commit("testing")

        DatasetCacheController.build().clear_all()

        r = fixture_working_dir_dataset_populated_scoped[2].execute(modified_query)
        assert 'errors' not in r
        d = r['data']['dataset']['modifiedOnUtc']
        modified_on_2 = aniso8601.parse_datetime(d)
        assert modified_on_2.microsecond == 0
        assert modified_on_2.tzname() == "+00:00"

        assert (datetime.datetime.now(datetime.timezone.utc) - modified_on_1).total_seconds() < 10
        assert (datetime.datetime.now(datetime.timezone.utc) - modified_on_2).total_seconds() < 10
        assert modified_on_2 > modified_on_1

    def test_get_commits_behind(self, fixture_working_dir):
        """Test temporar field commitsBehind on dataset objects"""
        im = InventoryManager(fixture_working_dir[0])
        ds = im.create_dataset("default", "default", "test-ds", "gigantum_object_v1",
                               description="my first dataset",
                               author=GitAuthor(name="default", email="test@test.com"))

        lb = im.create_labbook("default", "default", "test-lb")

        im.link_dataset_to_labbook(f"{ds.root_dir}/.git", 'default', 'test-ds', lb)

        query = """
                {
                  labbook(owner: "default", name:"test-lb")
                  {
                    linkedDatasets{
                      name
                      commitsBehind
                      
                    }
                  }
                }
                """
        r = fixture_working_dir[2].execute(query)
        assert 'errors' not in r
        assert r['data']['labbook']['linkedDatasets'][0]['name'] == 'test-ds'
        assert r['data']['labbook']['linkedDatasets'][0]['commitsBehind'] == 0

        ds.write_readme("test contents to make a commit")
        
        r = fixture_working_dir[2].execute(query)
        assert 'errors' not in r
        assert r['data']['labbook']['linkedDatasets'][0]['name'] == 'test-ds'
        assert r['data']['labbook']['linkedDatasets'][0]['commitsBehind'] == 1
