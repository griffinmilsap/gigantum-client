import redis
import datetime
from abc import ABC, abstractmethod
from typing import Tuple, Optional

from gtmcore.logging import LMLogger
from gtmcore.inventory.inventory import InventoryManager

logger = LMLogger.get_logger()


class RepoCacheEntry(ABC):
    """ Represents a specific entry in the cache for a specific Repository """

    # Entries become stale after 24 hours
    REFRESH_PERIOD_SEC = 60 * 60 * 24

    def __init__(self, redis_conn: redis.StrictRedis, key: str):
        self.db = redis_conn
        self.key = key

    def __str__(self):
        return f"RepoCacheEntry({self.key})"

    @staticmethod
    def _extract_id(key_value: str) -> Tuple[str, str, str]:
        token, user, owner, name = key_value.rsplit('&', 3)
        return user, owner, name

    @abstractmethod
    def _load_repo(self) -> Tuple[datetime.datetime, datetime.datetime, str]:
        pass

    def fetch_cachable_fields(self) -> Tuple[datetime.datetime, datetime.datetime, str]:
        logger.debug(f"Fetching {self.key} fields from disk.")
        self.clear()
        create_ts, modify_ts, description = self._load_repo()
        self.db.hset(self.key, 'description', description)
        self.db.hset(self.key, 'creation_date', modify_ts.strftime("%Y-%m-%dT%H:%M:%S.%f"))
        self.db.hset(self.key, 'modified_on', modify_ts.strftime("%Y-%m-%dT%H:%M:%S.%f"))
        self.db.hset(self.key, 'last_cache_update', datetime.datetime.utcnow().isoformat())
        return create_ts, modify_ts, description

    @staticmethod
    def _date(bin_str: bytes) -> Optional[datetime.datetime]:
        """Return a datetime instance from byte-string, but return None if input is None"""
        if bin_str is None:
            return None
        date = datetime.datetime.strptime(bin_str.decode(), "%Y-%m-%dT%H:%M:%S.%f")
        return date.replace(tzinfo=datetime.timezone.utc)

    def _fetch_property(self, hash_field: str) -> bytes:
        """Retrieve all cache-able fields from the given repo"""
        last_update = self._date(self.db.hget(self.key, 'last_cache_update'))
        if last_update is None:
            self.fetch_cachable_fields()
            last_update = self._date(self.db.hget(self.key, 'last_cache_update'))
        if last_update is None:
            raise ValueError("Cannot retrieve last_cache_update_field")
        delay_secs = (datetime.datetime.now(tz=datetime.timezone.utc) - last_update).total_seconds()
        if delay_secs > self.REFRESH_PERIOD_SEC:
            self.fetch_cachable_fields()
        return self.db.hget(self.key, hash_field)

    @property
    def modified_on(self) -> datetime.datetime:
        d = self._date(self._fetch_property('modified_on'))
        if d is None:
            raise ValueError("Cannot retrieve modified_on")
        else:
            return d

    @property
    def created_time(self) -> datetime.datetime:
        d = self._date(self._fetch_property('creation_date'))
        if d is None:
            raise ValueError("Cannot retrieve creation_date")
        else:
            return d

    @property
    def description(self) -> str:
        return self._fetch_property('description').decode()

    def clear(self):
        """Remove this entry from the Redis cache. """
        logger.warning(f"Flushing cache entry for {self}")
        self.db.hdel(self.key, 'creation_date', 'modified_on', 'last_cache_update', 'description')


class LabbookCacheEntry(RepoCacheEntry):
    def _load_repo(self) -> Tuple[datetime.datetime, datetime.datetime, str]:
        lb = InventoryManager().load_labbook(*self._extract_id(self.key))
        return lb.creation_date, lb.modified_on, lb.description


class DatasetCacheEntry(RepoCacheEntry):
    def _load_repo(self) -> Tuple[datetime.datetime, datetime.datetime, str]:
        ds = InventoryManager().load_dataset(*self._extract_id(self.key))
        return ds.creation_date, ds.modified_on, ds.description


class RepoCacheController:
    """
    This class represents an interface to the cache that stores specific
    repository fields (modified time, created time, description). The
    `cached_*` methods retrieve the given fields, and insert it into the cache
    if needed to be re-fetched.
    """
    def __init__(self, cache_token: str, cache_entry_type):
        """ Note: Intended to be a PRIVATE constructor"""
        self.db = redis.StrictRedis(db=7)
        self.cache_token = cache_token
        self.cache_entry_type = cache_entry_type

    @classmethod
    def build(cls):
        raise NotImplemented()

    def _make_key(self, id_tuple: Tuple[str, str, str]) -> str:
        return '&'.join([self.cache_token, *id_tuple])

    def cached_modified_on(self, id_tuple: Tuple[str, str, str]) -> datetime.datetime:
        """ Retrieves the "modified_on" field of the given repository identified by `id_tuple`
        Args:
            id_tuple: Fields needed to uniqely identify this repository
        Returns:
            modified_on field, from cache if possible
        """
        return self.cache_entry_type(self.db, self._make_key(id_tuple)).modified_on

    def cached_created_time(self, id_tuple: Tuple[str, str, str]) -> datetime.datetime:
        """ Retrieves the "created_time" field of the given repository identified by `id_tuple`
        Args:
            id_tuple: Fields needed to uniqely identify this repository
        Returns:
            modified_on field, from cache if possible
        """
        return self.cache_entry_type(self.db, self._make_key(id_tuple)).created_time

    def cached_description(self, id_tuple: Tuple[str, str, str]) -> str:
        """ Retrieves the description field of the given repository identified by `id_tuple`
        Args:
            id_tuple: Fields needed to uniqely identify this repository
        Returns:
            description field, from cache if possible
        """
        return self.cache_entry_type(self.db, self._make_key(id_tuple)).description

    def clear_entry(self, id_tuple: Tuple[str, str, str]) -> None:
        """ Flush this entry from the cache - ie indicate it is stale """
        self.cache_entry_type(self.db, self._make_key(id_tuple)).clear()


class LabbookCacheController(RepoCacheController):
    @classmethod
    def build(cls):
        return cls('LABBOOK_CACHE', LabbookCacheEntry)


class DatasetCacheController(RepoCacheController):
    @classmethod
    def build(cls):
        return cls('DATASET_CACHE', DatasetCacheEntry)

