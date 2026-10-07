# Fantasy Scout

NFL Intelligence agent that answers natural language questions about players, injuries, matchups, and game decisions. Uses LangGraph for agent orchestration, Qdrant for vector storage, and Groq for LLM inference.

## Setup

- For dependency management, use `uv` and `pyproject.toml`. Do not use `pip` or a `requirements.txt` file.

## Stack

- Backend: FastAPI, Python 3.13, uvicorn
- Agent: LangGraph
- LLM: Undecided
- Embeddings: Nomic (free tier)
- Vector store: Qdrant Cloud
- Database: PostgreSQL via Supabase, asyncpg driver
- Scheduler: APScheduler embedded in FastAPI
- Observability: LangSmith or Langfuse
- Containerization: Docker Compose
- Web Search: Tavily free tier, cache aggressively
- Weather: Open-Meteo API
- Scraping: BeautifulSoup4 + httpx
- Data: Sleeper API -> SportsDataIO -> Tavily -> scraping (last resort)
- Frontend: Next.js, Tailwind CSS, shadcn/ui

## Commands

- Sync project dependencies: `uv sync`
- Run app: `uv run uvicorn main:app --reload`
- Add dependency: `uv add <package>`. Do not use `uv pip`.

A task is complete when the four commands below pass and a test exists for every new function.

- Format code: `uv run ruff format`
- Lint: `uv run ruff check`
- Type check: `uv run pyright`
- Run tests: `uv run pytest tests/ -v`
- Run tests with coverage: `uv run pytest tests/ --cov=. --cov-report=term-missing`

## Coding Standards

- Type hints on every function signature including return types
- Use Python best practices like comprehensions, generators and decorators
- Pydantic v2 for structured data, `model_dump()` not `dict()`
- `async def` for all FastAPI routes
- `httpx` for all HTTP calls, do not use `requests`
- `pathlib` for path management, do not use `os.path`
- Use f-strings over `str.format()` or `%` formatting
- try/except on all external API calls with specific error types
- Return error info in dict rather than raising from tool functions
- pytest, pytest-asyncio, pytest-cov for testing

## Structure

- `tools/`: one file per data source, standalone functions
- `rag/`: embedding, ingestion, retrieval
- `agent/`: LangGraph graph, state, nodes, prompts
- `api/`: FastAPI routes and schemas
- `scheduler/`: APScheduler jobs
- `db/`: models and connections
- `tests/`: unit, integration, end-to-end tests
