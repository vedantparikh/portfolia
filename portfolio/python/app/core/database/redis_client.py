"""JSON Redis wrapper. Values are JSON; keys are JSON strings of the caller's key."""

import json
import logging
import os
from typing import Any, Dict, List, Optional

import redis

logger = logging.getLogger(__name__)

_client: Optional["RedisClient"] = None


class RedisClient:
    """One connection pool, with JSON get and set."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        ex_seconds: int = 3600,
    ) -> None:
        self.ex_seconds = ex_seconds
        self.connection_pool = redis.ConnectionPool(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=True,
        )

    @classmethod
    def make_from_env(cls) -> "RedisClient":
        return cls(
            host=os.environ.get("REDIS_HOST", "localhost"),
            port=int(os.environ.get("REDIS_PORT", "6379")),
            db=int(os.environ.get("REDIS_DB", "0")),
            password=os.environ.get("REDIS_PASSWORD") or None,
            ex_seconds=int(os.environ.get("REDIS_EX_SECONDS", "3600")),
        )

    class RedisContextManager:
        def __init__(self, connection_pool: redis.ConnectionPool) -> None:
            self.connection_pool = connection_pool
            self.connection: Optional[redis.Redis] = None

        def __enter__(self) -> redis.Redis:
            self.connection = redis.Redis(connection_pool=self.connection_pool)
            return self.connection

        def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
            if self.connection:
                self.connection.close()

    def set(self, key: Any, value: Any, ex_seconds: Optional[int] = None) -> bool:
        ttl = self.ex_seconds if ex_seconds is None else ex_seconds
        try:
            with self.RedisContextManager(self.connection_pool) as client:
                return bool(client.set(json.dumps(key), json.dumps(value), ex=ttl))
        except Exception as exc:
            logger.error("Redis set failed: %s", exc)
            return False

    def get(self, key: Any) -> Any:
        try:
            with self.RedisContextManager(self.connection_pool) as client:
                raw = client.get(json.dumps(key))
            return json.loads(raw) if raw is not None else None
        except Exception as exc:
            logger.error("Redis get failed: %s", exc)
            return None

    def mset(self, mapping: Dict[Any, Any], ex_seconds: Optional[int] = None) -> bool:
        """Set many keys in one pipeline. An empty mapping is a no-op."""
        if not mapping:
            return True
        ttl = self.ex_seconds if ex_seconds is None else ex_seconds
        try:
            with self.RedisContextManager(self.connection_pool) as client:
                pipe = client.pipeline()
                for key, value in mapping.items():
                    pipe.set(json.dumps(key), json.dumps(value), ex=ttl)
                pipe.execute()
            return True
        except Exception as exc:
            logger.error("Redis mset failed: %s", exc)
            return False

    def mget(self, keys: List[Any]) -> Dict[Any, Any]:
        """Return the keys that are present. Missing keys are omitted."""
        if not keys:
            return {}
        try:
            encoded = [json.dumps(key) for key in keys]
            with self.RedisContextManager(self.connection_pool) as client:
                raw_values = client.mget(encoded)
            found = {}
            for key, raw in zip(keys, raw_values):
                if raw is not None:
                    found[key] = json.loads(raw)
            return found
        except Exception as exc:
            logger.error("Redis mget failed: %s", exc)
            return {}

    def getdel(self, key: Any) -> Any:
        try:
            with self.RedisContextManager(self.connection_pool) as client:
                raw = client.getdel(json.dumps(key))
            return json.loads(raw) if raw is not None else None
        except Exception as exc:
            logger.error("Redis getdel failed: %s", exc)
            return None

    def incr_with_ttl(self, key: Any, ex_seconds: int) -> int:
        """Increment a counter and set its TTL only on the first increment."""
        try:
            with self.RedisContextManager(self.connection_pool) as client:
                pipe = client.pipeline()
                encoded = json.dumps(key)
                pipe.incr(encoded)
                pipe.ttl(encoded)
                count, ttl = pipe.execute()
                if ttl < 0:
                    client.expire(encoded, ex_seconds)
            return int(count)
        except Exception as exc:
            logger.error("Redis incr failed: %s", exc)
            return 0

    def ping(self) -> bool:
        try:
            with self.RedisContextManager(self.connection_pool) as client:
                return bool(client.ping())
        except Exception as exc:
            logger.error("Redis ping failed: %s", exc)
            return False


def get_redis() -> RedisClient:
    """The process-wide client. The pool is created once."""
    global _client
    if _client is None:
        _client = RedisClient.make_from_env()
    return _client
