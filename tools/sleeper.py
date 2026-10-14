from typing import TypedDict, NotRequired
import httpx
from langchain_core.tools import tool
from pathlib import Path

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



# --------------------------------------------------------
# HTTP Request
# --------------------------------------------------------

async def _get(url_path: str) -> SleeperResult:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{BASE_URL}/{url_path}")
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