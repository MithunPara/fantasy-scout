from typing import TypedDict, NotRequired, Any
import httpx
import time
import asyncio
import json
import logging
from langchain_core.tools import tool
from pathlib import Path

logger = logging.getLogger(__name__)
_players_lock = asyncio.Lock()

# --------------------------------------------------------
# Constants
# --------------------------------------------------------

BASE_URL = "https://api.sleeper.app/v1"
# 6 hour cache TTL to avoid calling players endpoint too frequently, recommended once a day
# but need more frequent updates for injuries
PLAYERS_TTL_SECONDS = 6 * 60 * 60 
# Disk cache so the cache will survive restarts
PLAYERS_CACHE_FILE = Path(".cache/sleeper_players.json")

# --------------------------------------------------------
# Types
# --------------------------------------------------------

class SleeperResult(TypedDict):
    data: list[dict] | None
    error: str | None

# Fields to retrieve from player endpoint
class SleeperPlayerRaw(TypedDict):
    player_id: str
    full_name: str
    first_name: NotRequired[str]
    last_name: NotRequired[str]
    search_full_name: NotRequired[str]
    position: NotRequired[str | None]
    team: NotRequired[str | None]
    status: NotRequired[str | None]
    active: NotRequired[bool]
    injury_status: NotRequired[str | None]
    injury_notes: NotRequired[str | None]
    practice_participation: NotRequired[str | None]
    age: NotRequired[int | None]
    years_exp: NotRequired[int | None]

class PlayersCache(TypedDict):
    fetched_at: float
    data: dict[str, SleeperPlayerRaw] | None

# --------------------------------------------------------
# Cache
# --------------------------------------------------------

# Manual cache (for now)
_players_cache: PlayersCache = {"fetched_at": 0.0, "data": None}

# Cache functions synchronous because disk file reads/writes cannot be awaited

# Check if the cache is fresh still (under 6 hours since last API pull)
def _is_fresh() -> bool:
    age = time.time() - _players_cache["fetched_at"]
    return _players_cache["data"] is not None and age < PLAYERS_TTL_SECONDS

def _read_disk_cache() -> None:
    try:
        # loads to deserialize JSON into Python object. loads() expects a string unlike load(), pathlib read_text converts to in-memory string instead of file stream
        return json.loads(PLAYERS_CACHE_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        pass # Will occur in the first run where cache isn't set yet
    except (OSError, ValueError, TypeError) as e:
    # OSError covers errors like FileNotFound, ValueError will cover invalid JSON or wrong encoding
        logger.warning("Unreadable disk cache: %s", type(e).__name__)

def _save_disk_cache() -> None:
    try:
        # Create the parent cache folder if needed to store temp cache file
        PLAYERS_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = PLAYERS_CACHE_FILE.with_suffix(".tmp")
        # First write the JSON into temp file then replace main cache file so if any issues occur when writing to temp file,
        # original cache will be unaffected
        tmp.write_text(json.dumps(_players_cache), encoding="utf-8")
        tmp.replace(PLAYERS_CACHE_FILE)
    except (OSError, ValueError, TypeError) as e:
        logger.warning("Disk cache write failed: %s", type(e).__name__)

async def _get_players() -> SleeperResult:
    # Use a lock so concurrent tool calls will wait instead of potentially calling API multiple times
    async with _players_lock:
        if _players_cache["data"] is None:
            # Use asyncio.to_thread to make synchronous function awaitable
            loaded_cache = await asyncio.to_thread(_read_disk_cache)
            if loaded_cache is not None:
                _players_cache.update(loaded_cache)

# --------------------------------------------------------
# HTTP Request
# --------------------------------------------------------

async def _get(url_path: str, params: dict[str, Any]) -> SleeperResult:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{BASE_URL}/{url_path}", params=params)
            response.raise_for_status() # Raise exception for 4xx and 5xx errors
            return {"data": response.json(), "error": None}
    # Exception if client error when retrieving API result
    # Base error, consider returning more specific error messages
    except httpx.HTTPError as e: 
        return {"data": None, "error": f"Sleeper request failed: {e}"}
    except ValueError: # Bad JSON
        return {"data": None, "error": "Sleeper returned invalid JSON"}

# --------------------------------------------------------
# Parsers
# --------------------------------------------------------


# --------------------------------------------------------
# Public Tools
# --------------------------------------------------------

@tool
async def get_nfl_state() -> SleeperResult:
    return await _get("state/nfl")

@tool
async def get_injured_players() -> SleeperResult: