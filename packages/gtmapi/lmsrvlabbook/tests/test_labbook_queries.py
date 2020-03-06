import os
import time
import responses
import flask

from snapshottest import snapshot
from lmsrvlabbook.tests.fixtures import fixture_working_dir, fixture_working_dir_populated_scoped, fixture_test_file
from lmsrvlabbook.tests.fixtures import fixture_working_dir_env_repo_scoped, property_mocks_fixture
from gtmcore.files import FileOperations
from gtmcore.fixtures import ENV_UNIT_TEST_REPO, ENV_UNIT_TEST_BASE, ENV_UNIT_TEST_REV, flush_redis_repo_cache
import datetime
import pprint
import aniso8601

import gtmcore

from gtmcore.inventory.inventory import InventoryManager
from gtmcore.fixtures import remote_labbook_repo, mock_labbook
from gtmcore.gitlib.git import GitAuthor


class TestLabBookServiceQueries(object):
    def test_pagination_noargs(self, fixture_working_dir_populated_scoped, snapshot):
        query = """
                {
                labbookList{
                    localLabbooks {
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
        snapshot.assert_match(fixture_working_dir_populated_scoped[2].execute(query))

    def test_pagination_sort_az(self, fixture_working_dir_populated_scoped, snapshot):
        query = """
                {
                labbookList{
                    localLabbooks(orderBy: "name") {
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
        snapshot.assert_match(fixture_working_dir_populated_scoped[2].execute(query))

    def test_pagination_sort_az_reverse(self, fixture_working_dir_populated_scoped, snapshot):
        query = """
                {
                labbookList{
                    localLabbooks(orderBy: "name", sort: "desc") {
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
        snapshot.assert_match(fixture_working_dir_populated_scoped[2].execute(query))

    def test_pagination_sort_create(self, fixture_working_dir_populated_scoped, snapshot):
        query = """
                {
                labbookList{
                    localLabbooks(orderBy: "created_on") {
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
        snapshot.assert_match(fixture_working_dir_populated_scoped[2].execute(query))

    def test_pagination_sort_modified(self, fixture_working_dir_populated_scoped, snapshot):

        query = """
                {
                labbookList{
                    localLabbooks(orderBy: "modified_on") {
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
        snapshot.assert_match(fixture_working_dir_populated_scoped[2].execute(query))

        im = InventoryManager(fixture_working_dir_populated_scoped[0])
        lb = im.load_labbook("default", "default", "labbook4")
        with open(os.path.join(lb.root_dir, "code", "test.txt"), 'wt') as tf:
            tf.write("asdfasdf")
        lb.git.add_all()
        lb.git.commit("Changing the repo")

        # Run query again
        flush_redis_repo_cache()
        snapshot.assert_match(fixture_working_dir_populated_scoped[2].execute(query))

    def test_pagination_first_only(self, fixture_working_dir_populated_scoped, snapshot):
        query = """
                {
                labbookList{
                    localLabbooks(first: 3) {
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
        snapshot.assert_match(fixture_working_dir_populated_scoped[2].execute(query))

    def test_pagination_first_and_after(self, fixture_working_dir_populated_scoped, snapshot):
        # Nominal case
        query = """
                {
                labbookList{
                    localLabbooks(first: 4, after: "Mg==") {
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
                            startCursor
                            endCursor
                        }
                    }
                }
                }
                """
        snapshot.assert_match(fixture_working_dir_populated_scoped[2].execute(query))

        # Overrunning end of list of labbooks
        query = """
                {
                labbookList{
                    localLabbooks(first: 6, after: "Ng==") {
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
        snapshot.assert_match(fixture_working_dir_populated_scoped[2].execute(query))

        # Overrunning end of list of labbooks, returns empty set.
        query = """
                {
                labbookList{
                    localLabbooks(first: 6, after: "OA==") {
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
        snapshot.assert_match(fixture_working_dir_populated_scoped[2].execute(query))

    def test_pagination_last_only(self, fixture_working_dir_populated_scoped, snapshot):
        query = """
                {
                labbookList{
                    localLabbooks(last: 3) {
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
        snapshot.assert_match(fixture_working_dir_populated_scoped[2].execute(query))

    def test_pagination_last_and_before(self, fixture_working_dir_populated_scoped, snapshot):
        query = """
                {
                labbookList{
                    localLabbooks(last: 3, before: "Nw==") {
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
        snapshot.assert_match(fixture_working_dir_populated_scoped[2].execute(query))

        # Overrun start of list
        query = """
                {
                labbookList{
                    localLabbooks(last: 3, before: "MQ==") {
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
                            startCursor
                            endCursor
                        }
                    }
                }
                }
                """
        snapshot.assert_match(fixture_working_dir_populated_scoped[2].execute(query))

        # Overrun with no intersection (should return empty list)
        query = """
                {
                labbookList{
                    localLabbooks(last: 3, before: "MA==") {
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
                            startCursor
                            endCursor
                        }
                    }
                }
                }
                """
        snapshot.assert_match(fixture_working_dir_populated_scoped[2].execute(query))

    def test_pagination(self, fixture_working_dir_populated_scoped, snapshot):
        """Test pagination and cursors"""
        # Get LabBooks for the "logged in user" - Currently just "default"
        query = """
                {
                labbookList{
                    localLabbooks(first: 2, after: "MQ==") {
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
        snapshot.assert_match(fixture_working_dir_populated_scoped[2].execute(query))

        before_query = """
                    {
                    labbookList{
                        localLabbooks(last: 2, before: "Ng==") {
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
        snapshot.assert_match(fixture_working_dir_populated_scoped[2].execute(before_query))

    def test_labbook_schema_version(self, fixture_working_dir):
        # Get LabBooks for the "logged in user" - Currently just "default"
        query = """
        {
            currentLabbookSchemaVersion
        }
        """
        r = fixture_working_dir[2].execute(query)
        assert 'errors' not in r
        assert r['data']['currentLabbookSchemaVersion'] == 2

    def test_get_labbook(self, fixture_working_dir):
        """Test listing labbooks"""
        flush_redis_repo_cache()
        im = InventoryManager(fixture_working_dir[0])
        lb = im.create_labbook('default', 'default', 'labbook1', description="my test description",
                               author=GitAuthor(name="tester", email="tester@test.com"))

        # Get LabBooks for a single user - Don't get the ID field since it is a UUID
        query = """
        {
          labbook(name: "labbook1", owner: "default") {
            isDeprecated
            schemaVersion
            name
            sizeBytes
            description
            creationDateUtc
            activeBranchName
          }
        }
        """
        r = fixture_working_dir[2].execute(query)
        assert 'errors' not in r
        assert r['data']['labbook']['schemaVersion'] == 2
        assert r['data']['labbook']['isDeprecated'] == False
        assert int(r['data']['labbook']['sizeBytes']) > 10000
        assert int(r['data']['labbook']['sizeBytes']) < 40000
        assert r['data']['labbook']['activeBranchName'] == 'master'
        assert r['data']['labbook']['name'] == 'labbook1'
        d = r['data']['labbook']['creationDateUtc']
        n = aniso8601.parse_datetime(d)
        assert (datetime.datetime.now(tz=datetime.timezone.utc) - n).total_seconds() < 5
        assert n.microsecond == 0
        assert n.tzname() in ["+00:00"]

    def test_get_labbook_size_rediculously_huge(self, monkeypatch, fixture_working_dir):
        """Test listing labbooks"""
        # Create labbooks
        monkeypatch.setattr(gtmcore.files.FileOperations, 'content_size', lambda labbook: (2**32)*34)
        im = InventoryManager(fixture_working_dir[0])
        lb = im.create_labbook('default', 'default', 'unittest-labbook-1',
                               description="my test description",
                               author=GitAuthor(name="tester", email="tester@test.com"))

        # Get LabBooks for a single user - Don't get the ID field since it is a UUID
        query = """
        {
          labbook(name: "unittest-labbook-1", owner: "default") {
            sizeBytes
          }
        }
        """
        r = fixture_working_dir[2].execute(query)
        assert 'errors' not in r
        assert int(r['data']['labbook']['sizeBytes']) == (2**32)*34

    def test_list_labbooks_container_status(self, fixture_working_dir, snapshot):
        """Test listing labbooks"""
        im = InventoryManager(fixture_working_dir[0])
        im.create_labbook('default', 'default', 'labbook1', description="my first labbook1")
        im.create_labbook('default', 'default', 'labbook2', description="my first labbook2")
        im.create_labbook('test3', 'test3', 'labbook2', description="my first labbook3")

        flush_redis_repo_cache()
        # Get LabBooks for the "logged in user" - Currently just "default"
        query = """
        {
            labbookList{
                localLabbooks {
                    edges {
                        node {
                            name
                            description
                            environment{
                                imageStatus
                                containerStatus
                            }
                        }
                        cursor
                    }   
                }
            }
        }
        """
        snapshot.assert_match(fixture_working_dir[2].execute(query))

    def test_list_local_by_id(self, fixture_working_dir, snapshot):
        """Test listing labbooks"""
        im = InventoryManager(fixture_working_dir[0])
        im.create_labbook('default', 'default', 'labbook1', description="my first labbook1")
        im.create_labbook('default', 'default', 'labbook2', description="my first labbook2")
        im.create_labbook('default', 'default', 'labbook3', description="my first labbook3")

        query = """
        {
        labbookList{
            localLabbooks {
                edges {
                    node {
                       id
                    }                    
                }
            }
        }
        }
        """
        result1 = fixture_working_dir[2].execute(query)

        query = """
        {
            labbookList{
                localById(ids: ["TGFiYm9vazpkZWZhdWx0JmxhYmJvb2sx", "TGFiYm9vazpkZWZhdWx0JmxhYmJvb2sz", "notanid"]){
                    id
                    name
                    owner
                    description
                }
            }
        }
        """
        result2 = fixture_working_dir[2].execute(query)
        snapshot.assert_match(result2)

        assert result1['data']['labbookList']['localLabbooks']['edges'][0]['node']['id'] == result2['data']['labbookList']['localById'][0]['id']
        assert result1['data']['labbookList']['localLabbooks']['edges'][2]['node']['id'] == result2['data']['labbookList']['localById'][1]['id']

    def test_list_labbooks_container_status_no_labbooks(self, fixture_working_dir, snapshot):
        """Test listing labbooks when none exist"""
        # Get LabBooks for the "logged in user" - Currently just "default"
        query = """
        {
            labbookList{
                localLabbooks {
                    edges {
                        node {
                            name
                            description
                            environment {
                                imageStatus
                                containerStatus
                            }
                        }
                    cursor
                    }
                }
            }
        }
        """
        snapshot.assert_match(fixture_working_dir[2].execute(query))

    def test_list_files_code(self, fixture_working_dir, snapshot):
        im = InventoryManager(fixture_working_dir[0])
        lb = im.create_labbook('default', 'default', 'labbook1', description='my first labbook1')

        has_no_files_query = """
        {
            labbook(name: "labbook1", owner: "default") {
                code{
                    hasFiles
                }
            }
        }
        """
        resp = fixture_working_dir[2].execute(has_no_files_query)
        assert 'errors' not in resp
        assert resp['data']['labbook']['code']['hasFiles'] is False

        # Write data in code
        with open(os.path.join(lb.root_dir, 'code', "test_file1.txt"), 'wt') as tf:
            tf.write("file 1")
        with open(os.path.join(lb.root_dir, 'code', "test_file2.txt"), 'wt') as tf:
            tf.write("file 2!!!!!!!!!")
        with open(os.path.join(lb.root_dir, 'code', ".hidden_file.txt"), 'wt') as tf:
            tf.write("Should be hidden")

        # Create subdirs and data
        os.makedirs(os.path.join(lb.root_dir, 'code', 'src', 'js'))
        with open(os.path.join(lb.root_dir, 'code', 'src', 'test.py'), 'wt') as tf:
            tf.write("print('hello, world')")
        with open(os.path.join(lb.root_dir, 'code', 'src', 'js', 'test.js'), 'wt') as tf:
            tf.write("asdfasdf")

        query = """
        {
            labbook(name: "labbook1", owner: "default") {
                name
                code {
                    files {
                        edges {
                            node {
                                id
                                key
                                size
                                isDir
                            }
                        }
                    }
                    hasFiles
                }
            }
        }
        """

        resp = fixture_working_dir[2].execute(query)
        assert 'errors' not in resp
        assert resp['data']['labbook']['code']['hasFiles'] is True
        snapshot.assert_match(resp)

        # Just get the files in the sub-directory "js"
        query = """
        {
            labbook(name: "labbook1", owner: "default") {
                name
                code {
                    files(rootDir: "src") {
                        edges {
                            node {
                                id
                                key
                                size
                                isDir
                            }
                        }
                    }
                }
            }
        }
        """
        snapshot.assert_match(fixture_working_dir[2].execute(query))

        # Just get the files in the sub-directory "js"
        query = """
                    {
                      labbook(name: "labbook1", owner: "default") {
                        name
                        code{
                            files(rootDir: "src/") {
                                edges {
                                    node {
                                        id
                                        key
                                        size
                                        isDir
                                    }
                                }
                            }
                        }
                      }
                    }
                    """
        snapshot.assert_match(fixture_working_dir[2].execute(query))

    def test_list_files_many(self, fixture_working_dir, snapshot):
        # Add some extra files for listing
        im = InventoryManager(fixture_working_dir[0])
        lb = im.create_labbook('default', 'default', 'labbook1',  description="my first labbook1")

        # Write data in code
        with open(os.path.join(lb.root_dir, 'code', "test_file1.txt"), 'wt') as tf:
            tf.write("file 1")
        with open(os.path.join(lb.root_dir, 'code', "test_file2.txt"), 'wt') as tf:
            tf.write("file 2!!!!!!!!!")
        with open(os.path.join(lb.root_dir, 'code', ".hidden_file.txt"), 'wt') as tf:
            tf.write("Should be hidden")

        # Create subdirs and data
        os.makedirs(os.path.join(lb.root_dir, 'input', 'subdir', 'data'))
        os.makedirs(os.path.join(lb.root_dir, 'output', 'empty'))
        with open(os.path.join(lb.root_dir, 'input', 'subdir', 'data.dat'), 'wt') as tf:
            tf.write("adsfasdfasdf")
        with open(os.path.join(lb.root_dir, 'output', 'result.dat'), 'wt') as tf:
            tf.write("fgh")

        query = """
                    {
                      labbook(name: "labbook1", owner: "default") {
                        name
                        code{
                            files {
                                edges {
                                    node {
                                        id
                                        key
                                        size
                                        isDir
                                    }
                                }
                            }
                        }
                        input{
                            files {
                                edges {
                                    node {
                                        id
                                        key
                                        size
                                        isDir
                                    }
                                }
                            }
                        }
                        output{
                            files {
                                edges {
                                    node {
                                        id
                                        key
                                        size
                                        isDir
                                    }
                                }
                            }
                        }
                      }
                    }
                    """
        r = fixture_working_dir[2].execute(query)
        snapshot.assert_match(r)

        # Just get the files in the sub-directory "js"
        query = """
                {
                  labbook(name: "labbook1", owner: "default") {
                    name
                    code{
                        files {
                            edges {
                                node {
                                    id
                                    key
                                    size
                                    isDir
                                }
                            }
                        }
                    }
                    input{
                        files(rootDir: "subdir") {
                            edges {
                                node {
                                    id
                                    key
                                    size
                                    isDir
                                }
                            }
                        }
                    }
                    output{
                        files(rootDir: "empty") {
                            edges {
                                node {
                                    id
                                    key
                                    size
                                    isDir
                                }
                            }
                        }
                    }
                  }
                }
                """
        r = fixture_working_dir[2].execute(query)
        snapshot.assert_match(r)

    def test_list_files(self, fixture_working_dir, snapshot):
        """Test listing labbook files"""

        im = InventoryManager(fixture_working_dir[0])
        lb = im.create_labbook('default', 'default', 'labbook1', description="my first labbook1")

        # Setup some favorites in code
        with open(os.path.join(lb.root_dir, 'code', 'test1.txt'), 'wt') as test_file:
            test_file.write("blah1")
        with open(os.path.join(lb.root_dir, 'code', 'test2.txt'), 'wt') as test_file:
            test_file.write("blah2")

        # Setup a favorite dir in input
        os.makedirs(os.path.join(lb.root_dir, 'code', 'blah'))

        # Get LabBooks for the "logged in user" - Currently just "default"
        query = """
        {
            labbook(name: "labbook1", owner: "default") {
                name
                code {
                    files {
                        edges {
                            node {
                                id
                                key
                                size
                                isDir
                            }
                        }
                    }
                }
            }
        }"""
        snapshot.assert_match(fixture_working_dir[2].execute(query))

    def test_list_all_files_many(self, fixture_working_dir, snapshot):
        # Add some extra files for listing
        im = InventoryManager(fixture_working_dir[0])
        lb = im.create_labbook("default", "default", "labbook1", description="my first labbook1")

        # Write data in code
        with open(os.path.join(lb.root_dir, 'code', "test_file1.txt"), 'wt') as tf:
            tf.write("file 1")
        with open(os.path.join(lb.root_dir, 'code', "test_file2.txt"), 'wt') as tf:
            tf.write("file 2!!!!!!!!!")
        with open(os.path.join(lb.root_dir, 'code', ".hidden_file.txt"), 'wt') as tf:
            tf.write("Should be hidden")

        # Create subdirs and data
        os.makedirs(os.path.join(lb.root_dir, 'input', 'subdir', 'data'))
        os.makedirs(os.path.join(lb.root_dir, 'output', 'empty'))
        with open(os.path.join(lb.root_dir, 'input', 'subdir', 'data.dat'), 'wt') as tf:
            tf.write("adsfasdfasdf")
        with open(os.path.join(lb.root_dir, 'output', 'result.dat'), 'wt') as tf:
            tf.write("fgh")

        query = """
                    {
                      labbook(name: "labbook1", owner: "default") {
                        name
                        code{
                            allFiles {
                                edges {
                                    node {
                                        id
                                        key
                                        size
                                        isDir
                                    }
                                }
                            }
                        }
                        input{
                            allFiles {
                                edges {
                                    node {
                                        id
                                        key
                                        size
                                        isDir
                                    }
                                }
                            }
                        }
                        output{
                            allFiles {
                                edges {
                                    node {
                                        id
                                        key
                                        size
                                        isDir
                                    }
                                }
                            }
                        }
                      }
                    }
                    """
        r = fixture_working_dir[2].execute(query)
        snapshot.assert_match(r)

    def test_get_activity_records_next_page(self, fixture_working_dir_env_repo_scoped, snapshot, fixture_test_file):
        """Test next page logic, which requires a labbook to be created properly with an activity"""
        # Create labbook
        query = """
        mutation myCreateLabbook($name: String!, $desc: String!, $repository: String!, 
                                 $base_id: String!, $revision: Int!) {
          createLabbook(input: {name: $name, description: $desc, 
                                repository: $repository, 
                                baseId: $base_id, revision: $revision}) {
            labbook {
              id
              name
              description
            }
          }
        }
        """
        variables = {"name": "labbook-page-test", "desc": "my test 1",
                     "base_id": ENV_UNIT_TEST_BASE, "repository": ENV_UNIT_TEST_REPO,
                     "revision": ENV_UNIT_TEST_REV}
        snapshot.assert_match(fixture_working_dir_env_repo_scoped[2].execute(query, variable_values=variables))

        im = InventoryManager(fixture_working_dir_env_repo_scoped[0])
        lb = im.load_labbook("default","default", "labbook-page-test")
        FileOperations.insert_file(lb, "code", fixture_test_file)

        # Get all records at once with no pagination args and verify cursors look OK directly
        query = """
        {
          labbook(name: "labbook-page-test", owner: "default") {
            name
            description
            activityRecords {
                edges{
                    node{
                        id
                        commit
                        linkedCommit
                        message
                        type
                        show
                        importance
                        tags
                        timestamp
                        }
                    cursor
                    }                    
                pageInfo{
                    startCursor
                    hasNextPage
                    hasPreviousPage
                    endCursor
                }
            }
          }
        }
        """
        result = fixture_working_dir_env_repo_scoped[2].execute(query)

        # Check cursors
        assert result['data']['labbook']['activityRecords']['pageInfo']['hasNextPage'] is False
        assert result['data']['labbook']['activityRecords']['pageInfo']['hasPreviousPage'] is False
        assert result['data']['labbook']['activityRecords']['edges'][-1]['node']['type'] == 'LABBOOK'

    def test_get_activity_records(self, fixture_working_dir, mock_labbook, snapshot, fixture_test_file):
        """Test paging through activity records"""
        im = InventoryManager(fixture_working_dir[0])
        lb = im.create_labbook('default', 'default', 'labbook11', description="my test description",
                               author=GitAuthor(name="tester", email="tester@test.com"))
        open('/tmp/test_file.txt', 'w').write("xxxx")
        FileOperations.insert_file(lb, "code", '/tmp/test_file.txt')
        open('/tmp/test_file.txt', 'w').write("xxxx")
        FileOperations.insert_file(lb, "input", '/tmp/test_file.txt')
        open('/tmp/test_file.txt', 'w').write("xxxx")
        FileOperations.insert_file(lb, "output", '/tmp/test_file.txt')

        # Get all records at once with no pagination args and verify cursors look OK directly
        query = """
        {
          labbook(name: "labbook11", owner: "default") {
            name
            description
            activityRecords {
                edges{
                    node{
                        id
                        commit
                        linkedCommit
                        message
                        type
                        show
                        importance
                        tags
                        timestamp
                        }
                    cursor
                    }                    
                pageInfo{
                    startCursor
                    endCursor
                }
            }
          }
        }
        """
        result = fixture_working_dir[2].execute(query)

        # Check cursors
        git_log = lb.git.log()
        assert result['data']['labbook']['activityRecords']['edges'][0]['cursor'] == git_log[0]['commit']
        assert result['data']['labbook']['activityRecords']['edges'][1]['cursor'] == git_log[2]['commit']
        assert result['data']['labbook']['activityRecords']['edges'][2]['cursor'] == git_log[4]['commit']

        assert result['data']['labbook']['activityRecords']['edges'][0]['node']['commit'] == git_log[0]['commit']
        assert result['data']['labbook']['activityRecords']['edges'][0]['node']['linkedCommit'] == git_log[1]['commit']

        # test timestamp field
        assert type(result['data']['labbook']['activityRecords']['edges'][0]['node']['timestamp']) == str
        assert result['data']['labbook']['activityRecords']['edges'][0]['node']['timestamp'][:2] == "20"

        assert type(result['data']['labbook']['activityRecords']['edges'][0]['node']['id']) == str
        assert len(result['data']['labbook']['activityRecords']['edges'][0]['node']['id']) > 0

        assert type(result['data']['labbook']['activityRecords']['pageInfo']['endCursor']) == str
        assert len(result['data']['labbook']['activityRecords']['pageInfo']['endCursor']) == 40

        # Get only the first record, verifying pageInfo and result via snapshot
        query = """
        {
          labbook(name: "labbook11", owner: "default") {
            name
            description
            activityRecords(first: 1) {
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
          }
        }
        """
        snapshot.assert_match(fixture_working_dir[2].execute(query))

        # Page 1 time
        query = """
        {{
          labbook(name: "labbook11", owner: "default") {{
            name
            description
            activityRecords(first: 2, after: "{}") {{
                edges{{
                    node{{                            
                        message
                        type
                        show
                        importance
                        tags
                        username
                        email
                        }}                        
                    }}                    
                pageInfo{{
                    hasNextPage
                    hasPreviousPage
                }}
            }}
          }}
        }}
        """.format(result['data']['labbook']['activityRecords']['edges'][0]['cursor'])
        snapshot.assert_match(fixture_working_dir[2].execute(query))

        # Page past end, expecting only the last result to come back
        query = """
        {{
          labbook(name: "labbook11", owner: "default") {{
            name
            description
            activityRecords(first: 5, after: "{}") {{
                edges{{
                    node{{                            
                        message
                        type
                        show
                        importance
                        tags
                        }}                        
                    }}                    
                pageInfo{{
                    hasNextPage
                    hasPreviousPage
                }}
            }}
          }}
        }}
        """.format(result['data']['labbook']['activityRecords']['edges'][1]['cursor'])
        snapshot.assert_match(fixture_working_dir[2].execute(query))

        # Page after end, expecting nothing to come back
        query = """
        {{
          labbook(name: "labbook11", owner: "default") {{
            name
            description
            activityRecords(first: 5, after: "{}") {{
                edges{{
                    node{{                            
                        message
                        type
                        show
                        importance
                        tags
                        }}                        
                    }}                    
                pageInfo{{
                    hasNextPage
                    hasPreviousPage
                }}
            }}
          }}
        }}
        """.format(result['data']['labbook']['activityRecords']['edges'][2]['cursor'])
        snapshot.assert_match(fixture_working_dir[2].execute(query))

    def test_get_activity_records_reverse_error(self, fixture_working_dir, snapshot):
        im = InventoryManager(fixture_working_dir[0])
        lb = im.create_labbook('default', 'default', 'labbook12', description="my test description")

        # Get all records
        query = """
        {
          labbook(name: "labbook12", owner: "default") {
            name
            description
            activityRecords(before: "asdfasdf") {
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
          }
        }
        """
        # Uses an invalid string
        r = fixture_working_dir[2].execute(query)
        assert 'errors' in r
        snapshot.assert_match(r)

        query = """
        {
          labbook(name: "labbook12", owner: "default") {
            name
            description
            activityRecords(before: "asdfasdf", last: 3){
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
          }
        }
        """
        r = fixture_working_dir[2].execute(query)
        assert 'errors' in r
        snapshot.assert_match(r)

        query = """
        {
          labbook(name: "labbook12", owner: "default") {
            name
            description
            activityRecords(last: 3) {
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
          }
        }
        """
        r = fixture_working_dir[2].execute(query)
        assert 'errors'  in r
        snapshot.assert_match(r)

    def test_get_activity_records_with_details(self, fixture_working_dir, snapshot, fixture_test_file):
        """Test getting activity records with detail records"""
        im = InventoryManager(fixture_working_dir[0])
        lb = im.create_labbook('default', 'default', 'labbook11', description="my test description")
        open('/tmp/test_file.txt', 'w').write("xxx" * 50)
        FileOperations.insert_file(lb, "code", '/tmp/test_file.txt')
        open('/tmp/test_file.txt', 'w').write("xxx" * 50)
        FileOperations.insert_file(lb, "input", '/tmp/test_file.txt')
        open('/tmp/test_file.txt', 'w').write("xxx" * 50)
        FileOperations.insert_file(lb, "output", '/tmp/test_file.txt')

        # Get all records at once and verify varying fields exist properly
        query = """
        {
          labbook(name: "labbook11", owner: "default") {
            name
            description
            activityRecords {
                edges{
                    node{
                        id
                        commit
                        linkedCommit
                        message
                        type
                        show
                        importance
                        tags
                        detailObjects{
                            id
                            key
                            type
                            data
                            show
                            importance
                            tags
                            action
                        }
                        }                        
                    }    
            }
          }
        }
        """
        result = fixture_working_dir[2].execute(query)

        # Check ids and keys
        assert len(result['data']['labbook']['activityRecords']['edges'][0]['node']['detailObjects'][0]['id']) > 0
        assert type(result['data']['labbook']['activityRecords']['edges'][0]['node']['detailObjects'][0]['id']) == str
        assert len(result['data']['labbook']['activityRecords']['edges'][1]['node']['detailObjects'][0]['id']) > 0
        assert type(result['data']['labbook']['activityRecords']['edges'][1]['node']['detailObjects'][0]['id']) == str

        # Verify again using snapshot and only fields that will snapshot well
        query = """
        {
          labbook(name: "labbook11", owner: "default") {
            name
            description
            activityRecords {
                edges{
                    node{
                        message
                        type
                        show
                        importance
                        tags
                        detailObjects{
                            type
                            data
                            show
                            importance
                            tags
                            action
                        }
                        }                        
                    }    
            }
          }
        }
        """
        snapshot.assert_match(fixture_working_dir[2].execute(query))

    def test_get_detail_record(self, fixture_working_dir, snapshot, fixture_test_file):
        """Test getting detail record directly after an initial activity record query"""
        im = InventoryManager(fixture_working_dir[0])
        lb = im.create_labbook('default', 'default', 'labbook11', description="my test description")
        FileOperations.insert_file(lb, "code", fixture_test_file)

        # Get all records at once and verify varying fields exist properly
        query = """
        {
          labbook(name: "labbook11", owner: "default") {
            name
            description
            activityRecords(first: 2) {
                edges{
                    node{
                        detailObjects{
                            id
                            key
                            type                                
                            show
                            importance
                            tags
                        }
                        }                        
                    }    
            }
          }
        }
        """
        activity_result = fixture_working_dir[2].execute(query)

        # Load detail record based on the key you got back and verify key/id
        query = """
        {{
          labbook(name: "labbook11", owner: "default") {{
            name
            description
            detailRecord(key: "{}") {{
                id
                key
                type                                
                show
                importance
                tags 
                action
            }}
          }}
        }}
        """.format(activity_result['data']['labbook']['activityRecords']['edges'][0]['node']['detailObjects'][0]['key'])
        detail_result = fixture_working_dir[2].execute(query)
        assert detail_result['data']['labbook']['detailRecord']['key'] == \
               activity_result['data']['labbook']['activityRecords']['edges'][0]['node']['detailObjects'][0]['key']
        assert detail_result['data']['labbook']['detailRecord']['id'] == \
               activity_result['data']['labbook']['activityRecords']['edges'][0]['node']['detailObjects'][0]['id']
        assert detail_result['data']['labbook']['detailRecord']['action'] == "CREATE"

        # Try again in a snapshot compatible way, loading data as well
        query = """
        {{
          labbook(name: "labbook11", owner: "default") {{
            name
            description
            detailRecord(key: "{}") {{
                type                                
                show
                data
                importance
                tags 
            }}
          }}
        }}
        """.format(activity_result['data']['labbook']['activityRecords']['edges'][0]['node']['detailObjects'][0]['key'])
        snapshot.assert_match(fixture_working_dir[2].execute(query))

    def test_get_detail_records(self, fixture_working_dir, snapshot, fixture_test_file):
        """Test getting multiple detail records directly after an initial activity record query"""
        im = InventoryManager(fixture_working_dir[0])
        lb = im.create_labbook("default", "default", "labbook11", description="my test description")
        open('/tmp/test_file.txt', 'w').write("xxxx")
        FileOperations.insert_file(lb, "code", '/tmp/test_file.txt')
        open('/tmp/test_file.txt', 'w').write("xxxx")
        FileOperations.insert_file(lb, "input", '/tmp/test_file.txt')

        # Get all records at once and verify varying fields exist properly
        query = """
        {
          labbook(name: "labbook11", owner: "default") {
            name
            description
            activityRecords(first: 2) {
                edges{
                    node{
                        detailObjects{
                            id
                            key
                            type                                
                            show
                            importance
                            tags
                        }
                        }                        
                    }    
            }
          }
        }
        """
        activity_result = fixture_working_dir[2].execute(query)

        # create key list
        keys = [activity_result['data']['labbook']['activityRecords']['edges'][1]['node']['detailObjects'][0]['key'],
                activity_result['data']['labbook']['activityRecords']['edges'][0]['node']['detailObjects'][0]['key']]

        # Try again in a snapshot compatible way, loading data as well
        query = """
        {{
          labbook(name: "labbook11", owner: "default") {{
            name
            description
            detailRecords(keys: [{}]) {{
                type                                
                show
                data
                importance
                tags 
            }}
          }}
        }}
        """.format(",".join(f'"{k}"' for k in keys))
        snapshot.assert_match(fixture_working_dir[2].execute(query))

    def test_get_labbook_create_date(self, fixture_working_dir, snapshot):
        """Test getting a labbook's create date"""
        # Create labbooks
        im = InventoryManager(fixture_working_dir[0])
        lb = im.create_labbook('default', 'default', 'labbook1', description="my test description")

        query = """
        {
          labbook(name: "labbook1", owner: "default") {
            creationDateUtc
          }
        }
        """
        r = fixture_working_dir[2].execute(query)
        assert 'errors' not in r
        d = r['data']['labbook']['creationDateUtc']
        # using aniso8601 to parse because built-in datetime doesn't parse the UTC offset properly (configured for js)
        create_on = aniso8601.parse_datetime(d)
        assert create_on.microsecond == 0
        assert create_on.tzname() in ["+00:00"]

        # wait, add another commit, and remove the buildinfo file to test the fallback method for getting create date
        time.sleep(4)
        lb.write_readme("##Summary\nThis is my readme!!")

        r = fixture_working_dir[2].execute(query)
        assert 'errors' not in r
        d = r['data']['labbook']['creationDateUtc']
        create_on_fallback = aniso8601.parse_datetime(d)
        assert create_on_fallback.microsecond == 0
        assert create_on_fallback.tzname() in ["+00:00"]

        # Because there can be 1 second of drift between normal and fallback methods, be safe and check they are not 2
        # seconds apart.
        assert abs((create_on - create_on_fallback).seconds) < 2

    def test_get_labbook_modified_on(self, fixture_working_dir, snapshot):
        """Test getting a labbook's modifed date"""
        # Create labbooks
        im = InventoryManager(fixture_working_dir[0])
        lb = im.create_labbook('default', 'default', 'labbook1', description="my test description")

        modified_query = """
        {
          labbook(name: "labbook1", owner: "default") {
            modifiedOnUtc
          }
        }
        """
        r = fixture_working_dir[2].execute(modified_query)
        assert 'errors' not in r
        d = r['data']['labbook']['modifiedOnUtc']
        # using aniso8601 to parse because built-in datetime doesn't parse the UTC offset properly (configured for js)
        modified_on_1 = aniso8601.parse_datetime(d)
        assert modified_on_1.microsecond == 0
        assert modified_on_1.tzname() in ["+00:00"]

        time.sleep(2)
        lb.write_readme("##Summary\nThis is my readme!!")

        flush_redis_repo_cache()
        r = fixture_working_dir[2].execute(modified_query)
        assert 'errors' not in r
        d = r['data']['labbook']['modifiedOnUtc']
        modified_on_2 = aniso8601.parse_datetime(d)

        # On a local machine, this might take only 3 seconds! But on CI it can go very slow for unknown reasons
        assert (datetime.datetime.now(tz=datetime.timezone.utc) - modified_on_1).total_seconds() < 40
        assert (datetime.datetime.now(tz=datetime.timezone.utc) - modified_on_2).total_seconds() < 40
        assert modified_on_2 > modified_on_1

    @responses.activate
    def test_repository_name_is_available(self, fixture_working_dir, property_mocks_fixture):
        # Create repositories
        im = InventoryManager(fixture_working_dir[0])
        im.create_labbook('default', 'default', 'project-1', description="a project that exists")
        im.create_dataset('default', 'default', 'dataset-1', storage_type="gigantum_object_v1",
                          description="a project that exists")
        flask.g.access_token = "afaketoken"

        responses.add(responses.GET, 'https://repo.gigantum.io/api/v4/projects/default%2Fremote-project',
                      json=[{
                          "id": 26,
                          "description": "",
                      }],
                      status=200)

        responses.add(responses.GET, 'https://repo.gigantum.io/api/v4/projects/default%2Funique-name',
                      status=404)

        responses.add(responses.GET, 'https://repo.gigantum.io/api/v4/projects/default%2Ffailure',
                      status=500)

        query = """
        {
          repositoryNameIsAvailable(name: "project-1")
        }
        """
        r = fixture_working_dir[2].execute(query)
        assert 'errors' not in r
        assert r['data']['repositoryNameIsAvailable'] is False

        query = """
        {
          repositoryNameIsAvailable(name: "dataset-1")
        }
        """
        r = fixture_working_dir[2].execute(query)
        assert 'errors' not in r
        assert r['data']['repositoryNameIsAvailable'] is False

        query = """
        {
          repositoryNameIsAvailable(name: "remote-project")
        }
        """
        r = fixture_working_dir[2].execute(query)
        assert 'errors' not in r
        assert r['data']['repositoryNameIsAvailable'] is False

        query = """
        {
          repositoryNameIsAvailable(name: "unique-name")
        }
        """
        r = fixture_working_dir[2].execute(query)
        assert 'errors' not in r
        assert r['data']['repositoryNameIsAvailable'] is True

        query = """
        {
          repositoryNameIsAvailable(name: "failure")
        }
        """
        r = fixture_working_dir[2].execute(query)
        assert 'errors' not in r
        assert r['data']['repositoryNameIsAvailable'] is True

