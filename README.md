# CV Generator

Herramienta web para analizar la compatibilidad entre un CV y una oferta laboral, optimizar el CV con consejos concretos y generar un PDF adaptado a la oferta. Construida con **FastAPI** y una interfaz HTML/CSS/JS sin frameworks adicionales.

---

## ¿Qué hace?

La app expone tres funcionalidades a través de una interfaz de tres pestañas:

| Pestaña | Descripción |
|---|---|
| **Match con la oferta** | Compara el CV contra la oferta y devuelve un score (0–100), fortalezas, brechas de habilidades y recomendaciones. |
| **Optimizar CV** | Analiza el CV frente a la oferta y genera consejos estructurados en Markdown: palabras clave ATS, ajustes por sección y estrategia para compensar brechas. |
| **Generar CV** | Produce un PDF del CV reescrito y optimizado para la oferta, usando una de las plantillas disponibles. |

El CV se sube en formato **Markdown** (`.md`). La oferta laboral se lee automáticamente a partir de su URL pública.

---

## Arquitectura

```
Browser (HTML/CSS/JS)
      │
      ▼
FastAPI  (/api/v1/*)
      │
      ├── Jina AI Reader API   ← extrae texto limpio de la URL de la oferta
      │
      └── Proveedor LLM ──────┬── OpenRouter (API externa, modelos gratuitos)
                               └── Ollama      (modelo local, sin terceros)
```

### Stack

- **Backend:** Python 3.12, FastAPI, Uvicorn, Pydantic v2
- **Frontend:** HTML + CSS + JS vanilla, `marked.js`, `DOMPurify`
- **LLM:** OpenRouter (`google/gemma-3-27b-it:free` por defecto) u Ollama (`llama3.2` por defecto)
- **Scraping de ofertas:** [Jina AI Reader API](https://jina.ai/reader/)
- **PDF:** WeasyPrint + plantillas HTML/CSS propias
- **Gestión de dependencias:** Poetry
- **Linting:** Ruff + pre-commit
- **Contenedores:** Docker + Docker Compose

### Estructura del proyecto

```
.
├── main.py                      # Entrada de la aplicación
├── Makefile                     # Comandos de desarrollo y despliegue
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── src/
    ├── api/
    │   ├── router.py            # Registro de rutas
    │   └── endpoints/
    │       ├── comparativa.py   # POST /comparativa/
    │       └── cv.py            # POST /cv/generate  POST /cv/pdf
    ├── config/
    │   ├── settings.py          # Configuración centralizada (singleton)
    │   └── .env.example         # Plantilla de variables de entorno
    ├── schemas/
    │   └── comparativa.py       # Modelos Pydantic de request/response
    ├── services/
    │   ├── comparativa.py       # Lógica de pipeline match CV↔oferta
    │   └── cv_generator.py      # Lógica de consejos y generación de PDF
    ├── utils/
    │   ├── llm.py               # Cliente LLM para análisis de compatibilidad
    │   ├── cv_llm.py            # Cliente LLM para consejos y generación de CV
    │   └── reader.py            # Cliente Jina AI Reader
    └── web/
        ├── index.html           # Interfaz gráfica
        └── templates/
            ├── clasico.html     # Plantilla PDF estilo clásico
            └── moderno.html     # Plantilla PDF estilo moderno
```

---

## Requisitos previos

- **Python 3.12+** y **Poetry**
- **Docker** y **Docker Compose** (para ejecución en contenedor)
- Una clave de **[Jina AI Reader](https://jina.ai/reader/)** (gratuita)
- Según el proveedor LLM elegido:
  - **OpenRouter:** clave de API gratuita en [openrouter.ai/keys](https://openrouter.ai/keys)
  - **Ollama:** instalación local de [Ollama](https://ollama.com/) (solo para ejecución local sin Docker)

---

## Configuración

Copia el archivo de ejemplo y rellena tus claves:

```bash
cp src/config/.env.example src/config/.env
```

### Variables de entorno

```env
ENVIRONMENT="LOCAL"          # LOCAL | DOCKER — se ajusta automáticamente en Docker

# ── Jina AI Reader ────────────────────────────────────────────────────────────
LOCAL_JINA_AI="tu-clave-jina"
DOCKER_JINA_AI="tu-clave-jina"

# ── Proveedor LLM: "openrouter" | "ollama" ────────────────────────────────────
LOCAL_LLM_PROVIDER="openrouter"
DOCKER_LLM_PROVIDER="openrouter"

# ── OpenRouter (si LLM_PROVIDER=openrouter) ────────────────────────────────────
LOCAL_OPENROUTER_API_KEY="tu-clave-openrouter"
DOCKER_OPENROUTER_API_KEY="tu-clave-openrouter"
LOCAL_OPENROUTER_MODEL="google/gemma-3-27b-it:free"
DOCKER_OPENROUTER_MODEL="google/gemma-3-27b-it:free"

# ── Ollama (si LLM_PROVIDER=ollama) ───────────────────────────────────────────
LOCAL_OLLAMA_HOST="http://localhost:11434"
DOCKER_OLLAMA_HOST="http://ollama:11434"
LOCAL_OLLAMA_MODEL="llama3.2"
DOCKER_OLLAMA_MODEL="llama3.2"
```

> **Privacidad:** con `LLM_PROVIDER=openrouter` el contenido del CV y la oferta se envían a servidores externos. Con `LLM_PROVIDER=ollama` todo el procesamiento es local y no sale de tu máquina.

---

## Ejecución local (sin Docker)

```bash
# 1. Instalar dependencias
poetry install

# 2. Arrancar el servidor
poetry run uvicorn main:app --reload
```

Abre [http://localhost:8000](http://localhost:8000) en el navegador.

### Con Ollama en local

Asegúrate de que Ollama esté corriendo y el modelo descargado:

```bash
ollama pull llama3.2
ollama serve          # si no arranca automáticamente
```

Configura `LOCAL_LLM_PROVIDER=ollama` en el `.env` y arranca normalmente.

---

## Ejecución con Docker

El proveedor LLM se determina automáticamente según `DOCKER_LLM_PROVIDER` en el `.env`.

```bash
make up       # arranca la app (y Ollama si el proveedor es ollama)
make down     # detiene todos los servicios
make logs     # sigue los logs en tiempo real
```

### Detalles por proveedor

**OpenRouter** (`DOCKER_LLM_PROVIDER=openrouter`):

```
make up
# equivale a: docker compose up --build
# servicios: app
```

**Ollama** (`DOCKER_LLM_PROVIDER=ollama`):

```
make up
# equivale a: docker compose --profile ollama up --build
# servicios: app + ollama + ollama-init (descarga el modelo automáticamente)
```

El servicio `ollama-init` descarga el modelo configurado en `DOCKER_OLLAMA_MODEL` al primer arranque. Los modelos se persisten en el volumen `ollama_data` entre reinicios.

Para cambiar el modelo que descarga `ollama-init`, crea un `.env` en la raíz del proyecto:

```env
# .env  (raíz del proyecto, solo para Docker Compose)
OLLAMA_MODEL=qwen2.5:7b
```

---

## API

La documentación interactiva está disponible en [http://localhost:8000/docs](http://localhost:8000/docs).

### Endpoints

#### `POST /api/v1/comparativa/`
Compara el CV con la oferta y devuelve un score de compatibilidad.

| Campo | Tipo | Descripción |
|---|---|---|
| `job_url` | `form` | URL pública de la oferta laboral |
| `cv_file` | `file` | CV en formato `.md` (máx. 5 MB) |

**Respuesta:**
```json
{
  "job_url": "https://...",
  "cv_filename": "mi_cv.md",
  "status": "completed",
  "message": "Resumen del análisis...",
  "result": {
    "match_score": 78,
    "summary": "...",
    "strengths": ["..."],
    "skill_gaps": [{ "skill": "...", "present_in_cv": false, "relevance": "alta" }],
    "recommendations": ["..."]
  }
}
```

---

#### `POST /api/v1/cv/generate`
Analiza el CV frente a la oferta y devuelve consejos de optimización en Markdown.

| Campo | Tipo | Descripción |
|---|---|---|
| `job_url` | `form` | URL pública de la oferta laboral |
| `cv_file` | `file` | CV en formato `.md` (máx. 5 MB) |

**Respuesta:**
```json
{ "advice": "## Compatibilidad general\n\n..." }
```

---

#### `POST /api/v1/cv/pdf`
Genera un PDF del CV reescrito y optimizado para la oferta.

| Campo | Tipo | Descripción |
|---|---|---|
| `job_url` | `form` | URL pública de la oferta laboral |
| `cv_file` | `file` | CV en formato `.md` (máx. 5 MB) |
| `template` | `form` | Plantilla a usar: `clasico` \| `moderno` (defecto: `clasico`) |

**Respuesta:** archivo PDF (`application/pdf`) para descarga directa.

---

#### `GET /api/v1/config`
Devuelve la configuración pública de la app (usada por el frontend para mostrar el aviso de privacidad correcto).

```json
{ "llm_provider": "openrouter" }
```

---

## Desarrollo

```bash
# Lint y formato
poetry run pre-commit run --all-files

# Tests
poetry run pytest --cov=app tests/
```

### Añadir dependencias

No uses `pip install` directamente. Edita `pyproject.toml` manualmente y ejecuta:

```bash
poetry lock
poetry install
```

---

## Notas de seguridad

- Las claves de API se leen exclusivamente desde variables de entorno; nunca se incluyen en el código fuente.
- El archivo `.env` está excluido del contexto de build Docker (`.dockerignore`) y del repositorio (`.gitignore`).
- El contenido recibido del LLM se sanitiza con **DOMPurify** antes de insertarse en el DOM.
- Las URLs de ofertas laborales son validadas para bloquear peticiones a rangos de IP privados (protección SSRF).
