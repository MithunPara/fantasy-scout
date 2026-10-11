from typing import Annotated
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field

TeamAbbr = Annotated[str, Field(min_length=2, max_length=4, description="NFL team abbreviation")]

# May need to add validators to make API info match enum values
class InjuryDesignation(str, Enum):
    IR = "Injured Reserve"
    OUT = "Out"
    DOUBTFUL = "Doubtful"
    QUESTIONABLE = "Questionable"
    PROBABLE = "Probable"
    ACTIVE = "Active"

class Conference(str, Enum):
    NFC = "National Football Conference"
    AFC = "American Football Conference"

class GameStatus(str, Enum):
    SCHEDULED = "Scheduled"
    IN_PROGRESS = "In Progress"
    COMPLETE = "Complete"

class Player(BaseModel):
    player_id: str = Field(min_length=1, description="Source player ID")
    name: str = Field(min_length=1, description='Player full name')
    team: TeamAbbr
    position: str = Field(min_length=1, max_length=4, description="Player position")
    age: int | None = None
    years_exp: int | None = None

class Team(BaseModel):
    team_id: str = Field(min_length=1, description="Source team ID")
    name: str = Field(min_length=1, description='Full team name')
    abbreviation: TeamAbbr
    conference: Conference
    division: str 

class Injury(BaseModel):
    player: Player
    description: str
    severity: str | None = None
    status: InjuryDesignation
    expected_return: str | None = None
    reported_at: datetime | None = None
    last_updated: datetime | None = None

class Game(BaseModel):
    game_id: str = Field(min_length=1, description="Source game ID")
    season: int = Field(ge=2000, description="Season year")
    week_number: int = Field(description="Week number")
    game_date: datetime | None = None
    status: GameStatus
    home_team: Team
    away_team: Team
    home_team_score: int | None = None
    away_team_score: int | None = None

"""
# Player overall stats, should include the season, the week, games played, all stats, fantasy points, recent performance (or is that reasoning done by LLM?) 
class PlayerStats(BaseModel):
    player: Player

# Matchup context for a specific player, should include the player, opposing team, defensive ranking (rush vs pass defence, matched up defender, etc.), home vs away game performance, weather condition, etc.
class Matchup(BaseModel):

# Agent Output, should include player, recommendation, confidence, reasoning, risk/mitigating factors, etc.
class FantasyDecision(BaseModel):
"""
