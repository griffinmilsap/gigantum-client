import gtmcore.configuration
from lmsrvcore.caching import RepoCacheController, RepoCacheEntry

from gtmcore.fixtures import mock_labbook


class TestRepoCacheMiddleware:
    def test_correctness_via_cache(self, mock_labbook, monkeypatch):
        """
        Test that caching works properly by ensuring that the actual value in the labbook
        matches the value when retrieved via the cache.
        """
        c, _, lb = mock_labbook
        username = 'test'
        monkeypatch.setattr(gtmcore.configuration.configuration.Configuration, 'find_default_config', lambda _: c)
        r = RepoCacheController()
        r.clear_entry((username, lb.owner, lb.name))
        assert lb.description == r.cached_description((username, lb.owner, lb.name))
        assert lb.creation_date.utctimetuple() == r.cached_created_time((username, lb.owner, lb.name)).utctimetuple()
        assert lb.modified_on.utctimetuple() == r.cached_modified_on((username, lb.owner, lb.name)).utctimetuple()

    def test_clear_cache(self, mock_labbook, monkeypatch):
        """
        Test that the clear_entry method works properly and deletes the cache entry from Redis.
        """
        c, _, lb = mock_labbook
        username = 'test'
        monkeypatch.setattr(gtmcore.configuration.configuration.Configuration, 'find_default_config', lambda _: c)
        r = RepoCacheController()
        r.clear_entry((username, lb.owner, lb.name))

        # Retrieve the values and put them in the cache
        r.cached_description((username, lb.owner, lb.name))
        r.cached_created_time((username, lb.owner, lb.name))
        r.cached_modified_on((username, lb.owner, lb.name))
        r.clear_entry((username, lb.owner, lb.name))
        assert not r.db.hgetall(r._make_key((username, lb.owner, lb.name)))
