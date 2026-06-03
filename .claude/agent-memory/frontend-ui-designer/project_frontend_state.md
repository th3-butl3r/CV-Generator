---
name: project-frontend-state
description: Current state of the frontend, established UI patterns, endpoint contract, and CSS variables used across the project
metadata:
  type: project
---

## Current frontend state (2026-05-23)

Single file: `src/web/index.html`. Implements the CV-match form (job URL + .md file upload)
and a result panel. No other pages or templates exist yet.

**Why:** First iteration of the project. Backend pipeline (scraping + LLM) is still a stub
returning `status: "pending"`.

**How to apply:** Before adding any new page or component, check this file for established
patterns rather than inventing new ones.

---

## Established CSS variables (defined in `index.html` :root)

| Variable | Value |
|---|---|
| `--bg` | `#0f1117` |
| `--surface` | `#1a1d27` |
| `--surface-hover` | `#21263a` |
| `--border` | `#2d3148` |
| `--accent` | `#6c63ff` |
| `--accent-hover` | `#5a52e0` |
| `--text` | `#e2e4f0` |
| `--muted` | `#7b7f9e` |
| `--success` | `#4ade80` |
| `--error` | `#f87171` |
| `--radius` | `12px` |

These must be reused in all new pages/templates without modification.

---

## Backend endpoint contract

- **URL**: `POST /api/v1/comparativa/`
- **Content-Type**: `multipart/form-data`
- **Fields**: `job_url` (string, form), `cv_file` (file upload, `.md` only, max 5 MB)
- **Response (current)**: `{ job_url, cv_filename, status, message }`
- **Response (target after backend pipeline)**: adds `result: { match_score, summary, strengths, skill_gaps: [{ skill, present_in_cv, relevance }], recommendations }`
- **Errors**: `{ "detail": "<msg>" }` with codes 400, 413, 422

---

## Responsive breakpoints

- Mobile: `< 768px`
- Tablet: `768px – 1024px`
- Desktop: `> 1024px`

---

## Phase plan reference

Detailed implementation phases are documented in `spec/02_frontend_fases_implementacion.md`:
- Phase 1: Enrich result panel in `index.html` (no backend dependency)
- Phase 2: CV generator form (`cv-generator.html`) — blocked on backend endpoint definition
- Phase 3: CV templates in `src/web/templates/` — blocked on render strategy decision
- Phase 4: Multi-page navigation — blocked on Phase 2
