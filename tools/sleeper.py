from typing import TypedDict, NotRequired, Any, Literal
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

class RawResult(TypedDict):
    data: Any
    error: str | None

# Fields to retrieve from Sleeper player endpoint
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

# Fields we store
class ParsedPlayer(TypedDict):
    player_id: str
    full_name: str
    search_name: str
    position: str | None
    team: str | None
    status: str | None
    injury_status: str | None
    injury_notes: str | None
    practice_participation: str | None
    age: int | None
    years_exp: int | None

class PlayersResult(TypedDict):
    data: dict[str, ParsedPlayer] | None
    error: str | None

class PlayersListResult(TypedDict):
    data: list[ParsedPlayer] | None
    error: str | None
 
# If ParsedPlayer shape changes, need to delete the cache file so the old format is not used
class PlayersCache(TypedDict):
    fetched_at: float
    data: dict[str, ParsedPlayer] | None

class TrendingPlayer(TypedDict):
    player: ParsedPlayer | None
    player_id: str
    count: int

class TrendingResult(TypedDict):
    data: list[TrendingPlayer] | None
    error: str | None

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

def _read_disk_cache() -> PlayersCache | None:
    try:
        # loads to deserialize JSON into Python object. loads() expects a string unlike load(), pathlib read_text converts to in-memory string instead of file stream
        payload = json.loads(PLAYERS_CACHE_FILE.read_text(encoding="utf-8"))

        if not isinstance(payload, dict) or not isinstance(payload.get("data"), dict):
            return None
        return {"fetched_at": float(payload["fetched_at"]), "data": payload["data"]}
    except FileNotFoundError:
        return None # Will occur in the first run where cache isn't set yet
    except (OSError, ValueError, TypeError, KeyError) as e:
    # ValueError will cover invalid JSON or wrong encoding
        logger.warning("Unreadable disk cache: %s", type(e).__name__)
        return None

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

# If memory cache is empty, load into it and return the cached data if it is fresh (within 6 hours). Otherwise, fetch players API endpoint and return. 
# If there is an error fetching, return stale cached data. If cache is empty and error fetching, return the API result error. 
async def _get_players() -> PlayersResult:
    # Use a lock so concurrent tool calls will wait instead of potentially calling API multiple times
    async with _players_lock:
        if _players_cache["data"] is None:
            # Use asyncio.to_thread to make synchronous function awaitable
            loaded_cache = await asyncio.to_thread(_read_disk_cache)
            if loaded_cache is not None:
                _players_cache.update(loaded_cache)
        if _is_fresh():
            return {"data": _players_cache["data"], "error": None}

        api_result = await _get("players/nfl", params={"active": "true"})
        if api_result["error"] is None and isinstance(api_result["data"], dict):
            parsed = _parse_players(api_result["data"])
            _players_cache["data"] = parsed
            # Update in-memory cache with current fetch time
            _players_cache["fetched_at"] = time.time()
            await asyncio.to_thread(_save_disk_cache)
            return {"data": parsed, "error": None}

        if _players_cache["data"] is not None:
            return {"data": _players_cache["data"], "error": None}
        return {"data": None, "error": api_result["error"] or "Unexpected players response shape"}

# --------------------------------------------------------
# HTTP Request
# --------------------------------------------------------

async def _get(url_path: str, params: dict[str, Any] | None = None) -> RawResult:
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

# Convert name to lower case with no spaces
def _normalize_name(name: str) -> str:
    return "".join(c for c in name.lower() if c.isalnum())

def _parse_player(raw: SleeperPlayerRaw) -> ParsedPlayer | None:
    player_id = raw.get("player_id")

    full_name = raw.get("full_name") or " ".join(
        part for part in (raw.get("first_name"), raw.get("last_name")) if part
    )

    # No player id or name can be extracted from the player record
    if not player_id or not full_name:
        return None

    return {
        "player_id": player_id,
        "full_name": full_name,
        "search_name": raw.get("search_full_name") or _normalize_name(full_name),
        "position": raw.get("position"),
        "team": raw.get("team"),
        "status": raw.get("status"),
        "injury_status": raw.get("injury_status"),
        "injury_notes": raw.get("injury_notes"),
        "practice_participation": raw.get("practice_participation"),
        "age": raw.get("age"),
        "years_exp": raw.get("years_exp"),
    }

def _parse_players(raw_player_map: dict[str, SleeperPlayerRaw]) -> dict[str, ParsedPlayer]:
    return {
        player_id: parsed
        for player_id, raw in raw_player_map.items()
        if (parsed := _parse_player(raw)) is not None
    }

def _filter_players(
    players_map: dict[str, ParsedPlayer],
    team: str | None,
    position: str | None,
    injured_only: bool,
    # Add a limit parameter on returned players?
) -> list[ParsedPlayer]:
    team = team.upper() if team else None
    position = position.upper() if position else None

    player_matches: list[ParsedPlayer] = []
    for player in players_map.values():
        if team and player["team"] != team:
            continue
        if position and player["position"] != position: 
            continue
        if injured_only and not player["injury_status"]:
            continue
        player_matches.append(player)

    return player_matches
# --------------------------------------------------------
# Public Tools
# --------------------------------------------------------

@tool
async def get_nfl_state() -> RawResult:
    """Get the current NFL season state.

    Use this first when you need to know what "this week" or "this season" is.
    
    Returns:
        dict with keys 'data' and 'error'. On success 'data' is a dict with
        'season' (str), 'week' (int), 'season_type' (str: 'pre', 'regular'
        or 'post') and 'display_week' (int); 'error' is None.
        On failure 'data' is None and 'error' is a message.
    """
    return await _get("state/nfl")

@tool
async def get_injured_players(
    team: str | None = None,
    position: str | None = None
) -> PlayersListResult:
    """List NFL players who currently have an injury designation.

    Injury data is a periodic snapshot and may lag official reports.

    Args:
        team: Optional team abbreviation such as 'KC' or 'BUF'.
        position: Optional position such as 'QB', 'RB', 'WR', 'TE'.

    Returns:
        dict with 'data' and 'error'. On success 'data' is a list of players
        with keys 'player_id', 'full_name', 'position', 'team', 'status',
        'injury_status', 'injury_notes', 'practice_participation', 'age',
        'years_exp'; 'error' is None. On failure 'data' is None and 'error'
        is a message.
    """
    result = await _get_players()
    players_map = result["data"]
    if players_map is None:
        return {"data": None, "error": result["error"]}
    players = _filter_players(players_map, team, position, True)
    return {"data": players, "error": None}

@tool 
async def find_player(name: str, limit: int = 15) -> PlayersListResult:
    """Search NFL players by name (case-insensitive, partial match).

    Exact name matches are listed first. Names can be ambiguous, so check
    team and position to pick the right player.

    Args:
        name: Full or partial player name, e.g. 'Ja'Marr Chase' or 'chase'.
        limit: Maximum players to return (default 15).

    Returns:
        Same shape as get_injured_players.
    """
    normalized_name = _normalize_name(name)
    if not normalized_name:
        return {"data": None, "error": "invalid name, must contain letters only"}

    result = await _get_players()
    players_map = result["data"]
    if players_map is None:
        return {"data": None, "error": result["error"]}

    exact_matches: list[ParsedPlayer] = []
    partial_matches: list[ParsedPlayer] = []
    for player in players_map.values():
        if player["search_name"] == normalized_name:
            exact_matches.append(player)
        elif normalized_name in player["search_name"]:
            partial_matches.append(player)
    return {"data": (exact_matches + partial_matches)[:limit], "error": None}

@tool
async def get_trending_players(
    trend_type: Literal["add", "drop"] = "add",
    lookback_hours: int = 24
    # Add player limit parameter?
) -> TrendingResult:
    """Get players most added or dropped across Sleeper fantasy leagues.

    Args:
        trend_type: 'add' or 'drop'.
        lookback_hours: How far back to count, in hours (default 24, max 168).

    Returns:
        dict with 'data' and 'error'. On success 'data' is a list of dicts
        with 'player' (player details, or None if unknown), 'player_id' (str)
        and 'count' (int, number of adds or drops). Data from Sleeper.
    """
    if trend_type not in ("add", "drop"):
        return {"data": None, "error": "trend_type must be 'add' or 'drop'"}
    # Set maximum hours to look back to a week
    lookback_hours = max(1, min(lookback_hours, 168))

    trending = await _get(
        f"players/nfl/trending/{trend_type}",
        params={"lookback_hours": lookback_hours}             
    )
    if trending["error"] is not None:
        return {"data": None, "error": trending["error"]}
    if not isinstance(trending["data"], list):
        return {"data": None, "error": "Unexpected trending player response shape"}

    all_players = await _get_players()
    players_map = all_players["data"]
    if players_map is None:
        return {"data": None, "error": all_players["error"]}

    trending_players: list[TrendingPlayer] = []
    # Trending endpoint only returns player id so must cross check with full player list to retrieve the player details
    for item in trending["data"]:
        player_id = str(item.get("player_id", ""))
        trending_players.append(
            {
                "player": players_map.get(player_id),
                "player_id": player_id,
                "count": int(item.get("count", 0))
            }
        )
    return {"data": trending_players, "error": None}
