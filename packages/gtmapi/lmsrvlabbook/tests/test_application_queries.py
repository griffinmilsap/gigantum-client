import pprint
from lmsrvlabbook.tests.fixtures import fixture_working_dir


class TestLabManagerQueries(object):
    def test_get_build_info(self, fixture_working_dir):
        """Test getting the build info field"""
        query = """
        {
            buildInfo
        }
        """
        r = fixture_working_dir[2].execute(query)
        assert 'errors' not in r
        assert 'Gigantum Client :: ' in r['data']['buildInfo']
