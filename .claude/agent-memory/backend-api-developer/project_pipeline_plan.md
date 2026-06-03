---
name: project-pipeline-plan
description: 7-phase backend implementation plan for ComparativaService pipeline — scraping, LLM, settings, schema, tests
metadata:
  type: project
---

The backend implementation is structured in 7 ordered phases defined in `spec/01_backend_fases_implementacion.md`.

**Phase order and dependencies:**
1. Env preparation (`src/config/.env`, poetry install)
2. Centralized config (`src/config/settings.py` with pydantic-settings singleton)
3. Enriched schema (`src/schemas/comparativa.py` — adds `ComparativaResult`, `SkillGap`, optional `result` field)
4. Scraping client (`src/utils/scraping.py` — httpx + BeautifulSoup, async)
5. LLM client (`src/utils/llm.py` — openai SDK, json_object response format, 2-attempt retry)
6. ComparativaService pipeline (`src/services/comparativa.py` — orchestrates phases 4+5, errors return status="error")
7. Tests (`tests/unit/` + `tests/integration/`)

**New dependencies to add manually to pyproject.toml (main):** `pydantic-settings`, `httpx`, `beautifulsoup4`, `openai`
**New dev dependencies:** `pytest`, `pytest-asyncio`, `pytest-cov`

**Why:** Current `ComparativaService.comparar()` is a stub returning `status="pending"`. Full pipeline does not exist yet.

**How to apply:** When implementing any of these layers, follow the phase order. The endpoint at `src/api/endpoints/comparativa.py` does NOT change — only service and below.
