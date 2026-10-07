# Architecture

## Layer Rules

- Keep route handlers thin - auth, validation, one service call, response
- Validate all external input with Pydantic schema at the boundary
- Use dependency injection for all external services, database connections, and API clients
- Convert internal exceptions to the existing API error format
- Do not expose stack traces or database errors in responses

## Data Sources

- Priority order: Sleeper API -> SportsDataIO -> Tavily search -> scraping
- Never build a scraper as the primary data path
- nfl.com requires Playwright if scraping is needed, never raw BeautifulSoup on dynamic JS sites
- Pro Football Reference: use polite delays (2-3s) and cache if scraped
- Cache Tavily responses aggressively

## Dependencies

- `tools/` imports nothing from `agent/`, `api/`, `scheduler/`, or `db/`
- `rag/` imports nothing from `agent/` or `api/`
- `agent/` imports from `tools/` and `rag/` only
- `api/` imports from `agent/` only
- `scheduler/` imports from `tools/` and `rag/` only

## Constraints

- Changes involving more than 3 files require a plan first
- No refactoring outside the task scope
- Never substitute LangChain agents for LangGraph
