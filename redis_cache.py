import os
import json
import redis.asyncio as redis
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

# --- Redis Async Client Setup ---
REDIS_URL = os.getenv("REDIS_URL")
print("[Redis] RAW REDIS_URL:", REDIS_URL)  # Debug

if not REDIS_URL:
    raise RuntimeError("REDIS_URL is not set in environment")

parsed = urlparse(REDIS_URL)

if not all([parsed.hostname, parsed.port]):
    raise RuntimeError("REDIS_URL is missing components. Check format: redis://host:6389/0")

# Configure Redis client based on URL scheme (redis vs rediss)
redis_config = {
    'host': parsed.hostname,
    'port': int(parsed.port),
    'decode_responses': True
}

# Add authentication if provided
if parsed.username:
    redis_config['username'] = parsed.username
if parsed.password:
    redis_config['password'] = parsed.password

# Add SSL if using rediss://
if parsed.scheme == 'rediss':
    redis_config['ssl'] = True

redis_client = redis.Redis(**redis_config)

# --- Base Utility Functions ---

async def set_cache(key: str, value, ttl: int = None):
    """Set a value in Redis with optional TTL (in seconds)."""
    try:
        serialized = json.dumps(value)
        if ttl:
            await redis_client.setex(key, ttl, serialized)
        else:
            await redis_client.set(key, serialized)
    except Exception as e:
        print(f"[Redis] Error setting cache for {key}: {e}")

async def get_cache(key: str):
    """Retrieve and deserialize value from Redis."""
    try:
        cached = await redis_client.get(key)
        if cached:
            return json.loads(cached)
    except Exception as e:
        print(f"[Redis] Error getting cache for {key}: {e}")
    return None

async def delete_cache(key: str):
    """Delete a cache entry."""
    try:
        await redis_client.delete(key)
    except Exception as e:
        print(f"[Redis] Error deleting cache for {key}: {e}")

# --- Inbox (conversation list) Caching ---

async def cache_inbox(key: str, inbox_data: list, ttl: int = 120):
    await set_cache(key, inbox_data, ttl)

async def get_cached_inbox(key: str):
    return await get_cache(key)

async def invalidate_inbox(key: str):
    await delete_cache(key)

# --- Conversation Messages Caching ---

async def cache_conversation(convo_id: str, messages: list, ttl: int = 300):
    key = f"inbox:conversation:{convo_id}"
    await set_cache(key, messages, ttl)

async def get_cached_conversation(convo_id: str):
    return await get_cache(f"inbox:conversation:{convo_id}")

async def invalidate_conversation(convo_id: str):
    await delete_cache(f"inbox:conversation:{convo_id}")


# --- Lead List Caching ---

async def cache_lead_list(skip: int, limit: int, leads: list, ttl: int = 300):
    key = f"leads:list:skip={skip}:limit={limit}"
    await set_cache(key, leads, ttl)

async def get_cached_lead_list(skip: int, limit: int):
    key = f"leads:list:skip={skip}:limit={limit}"
    return await get_cache(key)

async def invalidate_lead_list(skip: int, limit: int):
    key = f"leads:list:skip={skip}:limit={limit}"
    await delete_cache(key)