from typing import Dict, Optional, Any, List, Tuple
import asyncio
import logging
from datetime import datetime, timedelta
import json
from pathlib import Path
import pickle
from collections import OrderedDict
import hashlib

from ..core.config import CacheConfig
from ..core.exceptions import CacheError
from ..utils.monitoring import monitor_task
from ..core.constants import (
  CACHE_CLEANUP_INTERVAL,
  CACHE_CLEANUP_THRESHOLD,
  DEFAULT_CACHE_TTL
)

logger = logging.getLogger(__name__)

class CacheKey:
  """Cache key generator and validator"""
  
  @staticmethod
  def generate(term: str, context: Dict[str, Any]) -> str:
      """Generate cache key from term and context"""
      # Create a deterministic string representation of the context
      context_str = json.dumps(context, sort_keys=True)
      
      # Combine term and context for key generation
      key_content = f"{term}:{context_str}"
      
      # Generate hash for the key
      return hashlib.sha256(key_content.encode()).hexdigest()

  @staticmethod
  def validate(key: str) -> bool:
      """Validate cache key format"""
      if not isinstance(key, str):
          return False
      if len(key) != 64:  # SHA-256 hash length
          return False
      try:
          int(key, 16)  # Validate hexadecimal
          return True
      except ValueError:
          return False

class CacheEntry:
  """Individual cache entry with metadata"""
  
  def __init__(
      self,
      key: str,
      value: Any,
      ttl: timedelta = DEFAULT_CACHE_TTL
  ):
      self.key = key
      self.value = value
      self.created_at = datetime.utcnow()
      self.accessed_at = self.created_at
      self.ttl = ttl
      self.access_count = 0

  def is_expired(self) -> bool:
      """Check if entry has expired"""
      return datetime.utcnow() > self.created_at + self.ttl

  def access(self) -> None:
      """Update access metadata"""
      self.accessed_at = datetime.utcnow()
      self.access_count += 1

  def to_dict(self) -> Dict:
      """Convert entry to dictionary format"""
      return {
          'key': self.key,
          'created_at': self.created_at.isoformat(),
          'accessed_at': self.accessed_at.isoformat(),
          'ttl_seconds': self.ttl.total_seconds(),
          'access_count': self.access_count
      }

class AnalysisCache:
  """Cache manager for search term analysis"""
  
  def __init__(self, config: CacheConfig):
      self.config = config
      self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
      self._lock = asyncio.Lock()
      self._cleanup_task: Optional[asyncio.Task] = None
      self._stats = {
          'hits': 0,
          'misses': 0,
          'evictions': 0
      }

  async def start(self) -> None:
      """Start cache manager and cleanup task"""
      if self.config.enabled:
          self._cleanup_task = asyncio.create_task(
              self._periodic_cleanup()
          )
          logger.info("Cache manager started")

  async def stop(self) -> None:
      """Stop cache manager and cleanup task"""
      if self._cleanup_task:
          self._cleanup_task.cancel()
          try:
              await self._cleanup_task
          except asyncio.CancelledError:
              pass
      logger.info("Cache manager stopped")

  @monitor_task
  async def get(
      self,
      term: str,
      context: Dict[str, Any]
  ) -> Optional[Any]:
      """Get value from cache"""
      if not self.config.enabled:
          return None
          
      key = CacheKey.generate(term, context)
      
      async with self._lock:
          entry = self._cache.get(key)
          
          if entry is None:
              self._stats['misses'] += 1
              return None
              
          if entry.is_expired():
              await self._remove(key)
              self._stats['misses'] += 1
              return None
              
          entry.access()
          self._stats['hits'] += 1
          return entry.value

  @monitor_task
  async def set(
      self,
      term: str,
      context: Dict[str, Any],
      value: Any,
      ttl: Optional[timedelta] = None
  ) -> None:
      """Set value in cache"""
      if not self.config.enabled:
          return
          
      key = CacheKey.generate(term, context)
      entry = CacheEntry(
          key,
          value,
          ttl or self.config.ttl
      )
      
      async with self._lock:
          # Check cache size limit
          if len(self._cache) >= self.config.max_size:
              await self._evict()
              
          self._cache[key] = entry

  async def _remove(self, key: str) -> None:
      """Remove entry from cache"""
      if key in self._cache:
          del self._cache[key]

  async def _evict(self) -> None:
      """Evict entries based on policy"""
      if not self._cache:
          return
          
      # Remove oldest entry
      self._cache.popitem(last=False)
      self._stats['evictions'] += 1

  async def _periodic_cleanup(self) -> None:
      """Periodically clean up expired entries"""
      while True:
          try:
              await asyncio.sleep(CACHE_CLEANUP_INTERVAL)
              await self._cleanup()
          except asyncio.CancelledError:
              break
          except Exception as e:
              logger.error(f"Cache cleanup error: {str(e)}")

  async def _cleanup(self) -> None:
      """Clean up expired entries"""
      async with self._lock:
          expired_keys = [
              key for key, entry in self._cache.items()
              if entry.is_expired()
          ]
          
          for key in expired_keys:
              await self._remove(key)

  async def clear(self) -> None:
      """Clear all cache entries"""
      async with self._lock:
          self._cache.clear()
          self._stats = {
              'hits': 0,
              'misses': 0,
              'evictions': 0
          }

  async def get_stats(self) -> Dict[str, Any]:
      """Get cache statistics"""
      total_requests = self._stats['hits'] + self._stats['misses']
      hit_rate = (
          self._stats['hits'] / total_requests
          if total_requests > 0 else 0
      )
      
      return {
          'size': len(self._cache),
          'max_size': self.config.max_size,
          'hit_rate': hit_rate,
          'hits': self._stats['hits'],
          'misses': self._stats['misses'],
          'evictions': self._stats['evictions']
      }

  async def save_to_disk(self, filepath: Path) -> None:
      """Save cache to disk"""
      async with self._lock:
          try:
              cache_data = {
                  'entries': {
                      key: {
                          'value': entry.value,
                          'metadata': entry.to_dict()
                      }
                      for key, entry in self._cache.items()
                  },
                  'stats': self._stats
              }
              
              with open(filepath, 'wb') as f:
                  pickle.dump(cache_data, f)
                  
          except Exception as e:
              raise CacheError(f"Failed to save cache to disk: {str(e)}")

  async def load_from_disk(self, filepath: Path) -> None:
      """Load cache from disk"""
      async with self._lock:
          try:
              with open(filepath, 'rb') as f:
                  cache_data = pickle.load(f)
              
              self._cache.clear()
              for key, data in cache_data['entries'].items():
                  entry = CacheEntry(
                      key=key,
                      value=data['value'],
                      ttl=timedelta(
                          seconds=data['metadata']['ttl_seconds']
                      )
                  )
                  self._cache[key] = entry
              
              self._stats = cache_data['stats']
              
          except Exception as e:
              raise CacheError(f"Failed to load cache from disk: {str(e)}")