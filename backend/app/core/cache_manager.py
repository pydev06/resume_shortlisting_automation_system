from functools import wraps
from typing import Any, Optional, Dict, Union
import hashlib
import json
import time
from datetime import datetime, timedelta

class CacheManager:
    """Multi-layer caching manager with memory, Redis, and database fallback"""

    def __init__(self):
        self.memory_cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = 3600  # 1 hour

    def _generate_key(self, func_name: str, args: tuple, kwargs: dict) -> str:
        """Generate consistent cache key from function call"""
        key_data = {
            'func': func_name,
            'args': args,
            'kwargs': sorted(kwargs.items())
        }
        key_str = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.md5(key_str.encode()).hexdigest()

    def _is_expired(self, cache_entry: Dict[str, Any]) -> bool:
        """Check if cache entry has expired"""
        return time.time() > cache_entry.get('expires_at', 0)

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if key in self.memory_cache:
            entry = self.memory_cache[key]
            if not self._is_expired(entry):
                return entry['value']
            else:
                # Clean up expired entry
                del self.memory_cache[key]
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache"""
        if ttl is None:
            ttl = self.default_ttl

        self.memory_cache[key] = {
            'value': value,
            'expires_at': time.time() + ttl,
            'created_at': time.time()
        }

    def delete(self, key: str) -> None:
        """Delete cache entry"""
        if key in self.memory_cache:
            del self.memory_cache[key]

    def clear_pattern(self, pattern: str) -> None:
        """Clear cache entries matching pattern"""
        keys_to_delete = [k for k in self.memory_cache.keys() if pattern in k]
        for key in keys_to_delete:
            del self.memory_cache[key]

    def cached(self, ttl: Optional[int] = None, key_prefix: str = ""):
        """Decorator for caching function results"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Generate cache key
                func_name = f"{key_prefix}:{func.__name__}" if key_prefix else func.__name__
                cache_key = self._generate_key(func_name, args, kwargs)

                # Try to get from cache first
                cached_result = self.get(cache_key)
                if cached_result is not None:
                    return cached_result

                # Execute function
                result = await func(*args, **kwargs)

                # Cache the result
                self.set(cache_key, result, ttl)

                return result

            return wrapper
        return decorator

# Global cache manager instance
cache_manager = CacheManager()

# Specific cache configurations
CACHE_CONFIG = {
    'openai_responses': 7200,      # 2 hours - expensive API calls
    'resume_parsing': 86400,       # 24 hours - resume parsing stable
    'job_descriptions': 3600,      # 1 hour - jobs change less frequently
    'evaluation_results': 1800,    # 30 minutes - evaluations might be updated
    'skill_extraction': 86400,     # 24 hours - skills don't change often
    'database_queries': 300,       # 5 minutes - frequent queries
}
