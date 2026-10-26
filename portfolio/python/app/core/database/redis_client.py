import hashlib
import json
import logging
import pickle
from functools import wraps
from typing import List

import redis

from config import settings
from core.utils.singletonmeta import SingletonMeta

logger = logging.getLogger(__name__)


def ensure_serializable_key(func):
    """A decorator which ensure that redis keys can be properly serialized."""

    @wraps(func)
    def _check_key(_self, key, *args, **kwargs):
        """check if the key is of a serializable type."""
        if not isinstance(key, str) and not isinstance(key, bytes):
            key = json.dumps(key)

        return func(_self, key, *args, **kwargs)

    return _check_key


class RedisClient(metaclass=SingletonMeta):
    """
    RedisClient to communicate with redis Server
    Redis Commands: https://redis.io/commands
    """

    class RedisContextManager:
        """A context manager for redis connection."""

        def __init__(self, connection_pool):
            self.connection_pool = connection_pool

        def __enter__(self):
            self.redis = redis.Redis(connection_pool=self.connection_pool)  # noqa pylint: disable=attribute-defined-outside-init
            try:
                self.redis.ping()
            except redis.ConnectionError:
                self.redis = None
            return self.redis

        def __exit__(self, exc_type, exc_val, exc_tb):
            if exc_tb:
                logger.error(
                    f"Error in Redis connection: {exc_type} {exc_val} {exc_tb}"
                )
            if self.redis is not None:
                self.redis.close()

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        connect: bool = False,
        password: str | None = None,
    ):
        self.host = host
        self.port = port
        self.db = db
        self.ex_seconds = settings.REDIS_TTL_SECONDS
        self.ex_seconds_model = settings.REDIS_TTL_MODEL_SECONDS
        self.connection_pool = redis.ConnectionPool(
            host=self.host,
            port=self.port,
            db=self.db,
            password=password or None,
            max_connections=1024,
            socket_timeout=5,
            health_check_interval=self.ex_seconds,
        )

    def __repr__(self):
        return f"RedisClient(host={self.host}, port={self.port}, db={self.db})"

    @classmethod
    def make_from_env(cls):
        """Build the client from application settings."""
        return cls(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD or None,
        )

    def set(self, key, value, ex_seconds=None):
        """SET the string value of a key."""

        # use the expiry time if client passes it or set it to global expiry time
        ex_seconds = ex_seconds or self.ex_seconds
        # -1 we use as no expiration
        if ex_seconds == -1:
            ex_seconds = None
        key = json.dumps(key)
        with self.RedisContextManager(self.connection_pool) as client:
            if client is not None:
                result = client.set(key, json.dumps(value), ex=ex_seconds)
                logger.info(f"Created new Redis cache with key: {key}.")

                return result

    def set_raw(self, resource, value, transformer_class, ex_seconds=None):
        """SET the string value of a key."""
        ex_seconds = ex_seconds or self.ex_seconds_model
        # -1 we use as no expiration
        if ex_seconds == -1:
            ex_seconds = None
        # we can transform same data with different transformers
        # (e.g. ParentEncounter with ParentEncounterTransformer or EncounterTransformer)
        key_str = repr(resource) + repr(transformer_class)
        cache_key = hashlib.sha512(key_str.encode()).hexdigest()
        value = pickle.dumps(value)

        with self.RedisContextManager(self.connection_pool) as client:
            if client is not None:
                result = client.set(cache_key, value, ex=ex_seconds)
                logger.info(
                    f"Created new Redis cache with instance: {resource['id'] + '_' + resource['resourceType']}."
                )

                return result

    def get(self, key):
        """GET the value of a key."""

        key = json.dumps(key)
        with self.RedisContextManager(self.connection_pool) as client:
            if client is not None:
                data = client.get(key)
                result = None
                if data:
                    logger.info(
                        f"Found Redis data for the given key: {key} from cache."
                    )
                    result = json.loads(data)
                else:
                    logger.info(f"Given key: {key} was not found.")
                return result

    def get_raw(self, resource, transformer_class) -> [dict, bool]:
        """GET the value of a key."""
        # we can transform same data with different transformers
        # (e.g. ParentEncounter with ParentEncounterTransformer or EncounterTransformer)
        key_str = repr(resource) + repr(transformer_class)
        cache_key = hashlib.sha512(key_str.encode()).hexdigest()
        data = None
        exist = False
        with self.RedisContextManager(self.connection_pool) as client:
            if client is not None:
                data = client.get(cache_key)
                # check if the data exists in cache, but it's None (e.g. ParentEncounter with EncounterTransformer)
                if data:
                    exist = True
                    data = pickle.loads(data)
                    logger.info(
                        f"Found Redis cache for model instance: "
                        f"{resource['resourceType'] + '_' + resource['id']} "
                    )
                else:
                    logger.info(
                        f"Given instance: "
                        f"{resource['resourceType'] + '_' + resource['id']} was not found or changed."
                    )

            return data, exist

    def getdel(self, key):
        """Atomically GET and DELETE a key. Returns None if missing or Redis is down."""

        key = json.dumps(key)
        with self.RedisContextManager(self.connection_pool) as client:
            if client is not None:
                data = client.getdel(key)
                return json.loads(data) if data else None

    def incr_with_ttl(self, key, ex_seconds: int):
        """
        Atomically increment a counter, setting its TTL when first created.
        Returns the new count, or None if Redis is unavailable.
        """

        key = json.dumps(key)
        with self.RedisContextManager(self.connection_pool) as client:
            if client is not None:
                pipe = client.pipeline()
                pipe.incr(key)
                pipe.expire(key, ex_seconds, nx=True)
                count, _ = pipe.execute()
                return count

    def delete(self, key):
        """DELETE a key."""

        key = json.dumps(key)
        with self.RedisContextManager(self.connection_pool) as client:
            if client is not None:
                return client.delete(key)

    def exists(self, key):
        """To check the given key exists in Redis db."""

        key = json.dumps(key)
        with self.RedisContextManager(self.connection_pool) as client:
            if client is not None:
                return client.exists(key)

    def clear_on_pattern(self, pattern: str):
        """
        This Function matches the input search pattern and deletes that
        specific redis resource containing the given `pattern`.
        """

        count = 1
        pattern = f"*{pattern}*"
        with self.RedisContextManager(self.connection_pool) as client:
            if client is not None:
                for key in client.scan_iter(match=pattern, count=10000):
                    client.unlink(key)
                    count += 1
                logging.info(f"Cleared cache for {pattern}.")
                return count

    def flush_db(self):
        """Deletes all cache from current."""
        with self.RedisContextManager(self.connection_pool) as client:
            if client is not None:
                client.flushdb()

    def flush_all(self):
        """Deletes all cache."""
        with self.RedisContextManager(self.connection_pool) as client:
            if client is not None:
                client.flushall(asynchronous=True)

    # @ensure_connection
    def get_matching_keys(self, pattern: str):
        """Returns cache keys"""
        with self.RedisContextManager(self.connection_pool) as client:
            if client is not None:
                return client.keys(f"*{pattern}*")

    def mset(self, items: dict, ex_seconds=None):
        """SET many keys in one pipeline. Keys and values are JSON, same as set()."""
        if not items:
            return
        ex_seconds = ex_seconds or self.ex_seconds
        if ex_seconds == -1:
            ex_seconds = None
        with self.RedisContextManager(self.connection_pool) as client:
            if client is not None:
                pipe = client.pipeline()
                for key, value in items.items():
                    pipe.set(json.dumps(key), json.dumps(value), ex=ex_seconds)
                pipe.execute()

    def mget(self, keys: List[str]):
        """Returns cache key value pairs"""
        byte_list = [json.dumps(item).encode() for item in keys]
        with self.RedisContextManager(self.connection_pool) as client:
            if client is not None:
                values = client.mget(byte_list)
                return {
                    key: json.loads(values[i])
                    for i, key in enumerate(keys)
                    if values[i] is not None
                }

    def ping(self):
        """Ping the Redis server."""
        with self.RedisContextManager(self.connection_pool) as client:
            if client is not None:
                return client.ping()


def get_redis():
    """get the redis client to use."""
    return RedisClient.make_from_env()
