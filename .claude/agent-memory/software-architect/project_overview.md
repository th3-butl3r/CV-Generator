---
name: project-overview
description: Estado inicial del proyecto CV-Generator — stack, dependencias, módulos existentes y el TODO principal en ComparativaService
metadata:
  type: project
---

# CV-Generator — Estado inicial (2026-05-22)

**Why:** Primera exploración del proyecto antes de diseñar la implementación del núcleo de negocio.

**How to apply:** Usar como baseline para cualquier decisión de diseño sobre el flujo scraping → LLM → respuesta.

## Stack confirmado
- Python 3.12+, FastAPI 0.136, Pydantic v2, Loguru, Poetry
- Sin pytest ni httpx en pyproject.toml todavía (solo pudb en dev)
- Pre-commit: black (line-length=90) + ruff + pre-commit-hooks estándar
- No hay dependencias de HTTP client (httpx, requests), ni LLM client (openai, anthropic), ni scraping (beautifulsoup4, playwright)

## Módulos existentes
- `main.py` — FastAPI app, monta /static y sirve index.html en /
- `src/api/router.py` — APIRouter principal, incluye comparativa con prefix /api/v1/comparativa
- `src/api/endpoints/comparativa.py` — POST / multipart: job_url (Form) + cv_file (.md, UploadFile). Valida URL, tamaño (5MB), extensión
- `src/services/comparativa.py` — ComparativaService.comparar() con TODO: scraping + LLM
- `src/schemas/comparativa.py` — ComparativaResponse(job_url, cv_filename, status, message) — minimalista, sin score ni skills
- `src/config/__init__.py` — vacío, sin lógica de carga de .env
- `src/web/index.html` — SPA minimalista que llama POST /api/v1/comparativa/ y muestra JSON raw

## TODO principal
`ComparativaService.comparar()` en `src/services/comparativa.py` — implementar:
1. Scraping del HTML de job_url
2. Extracción/parsing del texto de la oferta
3. Llamada a LLM con CV + oferta
4. Respuesta estructurada con score y análisis

## Variables de entorno
- `src/config/.env` existe pero su contenido es desconocido (no se leyó — secretos)
- `src/config/__init__.py` está vacío: la carga de settings con pydantic-settings aún no existe
