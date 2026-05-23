# Refactoring Roadmap: Implementación del núcleo de ComparativaService

- **Date**: 2026-05-22
- **Status**: Proposed

---

## Current State

`ComparativaService.comparar()` devuelve un stub con `status="pending"`. El pipeline real — scraping de la oferta laboral, parsing del texto, análisis LLM, respuesta estructurada — no existe. Los módulos de soporte (`config/`, `utils/`) están vacíos. No hay dependencias de HTTP client, LLM client ni scraping en `pyproject.toml`. No hay tests.

## Pain Points

1. `src/config/__init__.py` vacío: no hay gestión centralizada de settings ni validación de variables de entorno al arranque.
2. `ComparativaResponse` es demasiado pobre: no tiene score, skills, ni estructura que el frontend pueda consumir más allá de mensaje libre.
3. `ComparativaService` es una clase estática con un único método: no tiene inyección de dependencias, lo que dificulta el testing.
4. El scraping y la llamada LLM son operaciones de red de latencia variable (segundos): si se hacen síncronamente dentro del request/response cycle, el usuario espera sin feedback.
5. No hay manejo de errores de red en la capa de servicio (timeout, sitio bloqueado, LLM rate-limit).

## Target State

Un pipeline completamente async con tres capas bien separadas:

```
Endpoint → ComparativaService → [ScrapingClient + LLMClient] → ComparativaResponse (enriquecido)
                                        ↑
                               src/config/settings.py (pydantic-settings)
```

## Migration Steps (ordenados por prioridad)

### Paso 1 — Configuración centralizada

**Archivo nuevo:** `src/config/settings.py`

Responsabilidad: cargar y validar todas las variables de entorno al startup con `pydantic-settings`. Exponer un singleton `get_settings()`.

```python
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración global de la aplicación cargada desde .env."""

    llm_api_key: str
    llm_model: str = "gpt-4o-mini"
    llm_base_url: str = "https://api.openai.com/v1"
    scraping_timeout_seconds: int = 15
    scraping_user_agent: str = "CVGenerator/0.1"

    model_config = SettingsConfigDict(
        env_file="src/config/.env",
        env_file_encoding="utf-8",
    )


@lru_cache
def get_settings() -> Settings:
    """Retorna la instancia singleton de Settings."""
    return Settings()
```

> **Dependencia nueva requerida** (añadir manualmente a `pyproject.toml`): `pydantic-settings`.

---

### Paso 2 — Schema enriquecido

**Archivo a modificar:** `src/schemas/comparativa.py`

Añadir modelos que representen el resultado real del análisis. Mantener `ComparativaResponse` como modelo de respuesta HTTP para no romper el contrato existente del endpoint.

```python
from pydantic import BaseModel, Field


class SkillGap(BaseModel):
    """Representa una habilidad mencionada en la oferta y su estado en el CV."""

    skill: str
    present_in_cv: bool
    relevance: str = Field(description="alta | media | baja")


class ComparativaResult(BaseModel):
    """Resultado estructurado del análisis LLM."""

    match_score: int = Field(ge=0, le=100, description="Score de coincidencia 0-100")
    summary: str = Field(description="Resumen ejecutivo del análisis")
    strengths: list[str] = Field(default_factory=list)
    skill_gaps: list[SkillGap] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class ComparativaResponse(BaseModel):
    """Respuesta completa del endpoint /comparativa/."""

    job_url: str
    cv_filename: str
    status: str  # "completed" | "error"
    message: str
    result: ComparativaResult | None = None
```

El campo `result` es `None` cuando `status="error"`, lo que mantiene compatibilidad parcial con el frontend actual.

---

### Paso 3 — Cliente de scraping

**Archivo nuevo:** `src/utils/scraping.py`

Responsabilidad exclusiva: dado una URL, obtener el texto limpio de la página (sin HTML, scripts, estilos). No interpreta el contenido — solo extrae texto plano.

```python
from loguru import logger


async def fetch_job_description(url: str, timeout: int) -> str:
    """Descarga y extrae el texto de una oferta laboral desde su URL.

    Args:
        url: URL pública de la oferta laboral.
        timeout: Tiempo máximo de espera en segundos.

    Returns:
        Texto limpio del contenido de la oferta.

    Raises:
        ValueError: Si la URL no responde o el contenido está vacío.
    """
    logger.info(f"BL > fetch_job_description() - Iniciando scraping | url={url}")
    # httpx.AsyncClient + BeautifulSoup para extracción de texto
    ...
```

> **Dependencias nuevas requeridas:** `httpx`, `beautifulsoup4`.

---

### Paso 4 — Cliente LLM

**Archivo nuevo:** `src/utils/llm.py`

Responsabilidad exclusiva: construir el prompt, llamar al LLM y parsear la respuesta estructurada. Desacoplado de `ComparativaService` para poder testearlo y sustituirlo de forma independiente.

```python
from loguru import logger

from src.schemas.comparativa import ComparativaResult


async def analyze_cv_match(
    cv_content: str,
    job_description: str,
    api_key: str,
    model: str,
    base_url: str,
) -> ComparativaResult:
    """Llama al LLM para analizar la coincidencia CV-oferta.

    Args:
        cv_content: Contenido del CV en formato Markdown.
        job_description: Texto limpio de la oferta laboral.
        api_key: Clave de autenticación del proveedor LLM.
        model: Identificador del modelo a usar.
        base_url: URL base de la API del proveedor.

    Returns:
        ComparativaResult con score, skills y recomendaciones.

    Raises:
        RuntimeError: Si el LLM no retorna JSON parseable.
    """
    logger.info(f"BL > analyze_cv_match() - Llamando LLM | model={model}")
    # openai client con response_format={"type": "json_object"} o structured outputs
    ...
```

> **Dependencia nueva requerida:** `openai` (compatible con cualquier proveedor OpenAI-compatible vía `base_url`).

**Decisión de diseño:** usar `openai` SDK en vez de `httpx` directo porque soporta retry automático, manejo de rate-limit y providers alternativos (OpenRouter, Groq, Ollama local) solo cambiando `base_url` + `llm_api_key` en `.env`. No acopla el sistema a un único proveedor.

---

### Paso 5 — Implementar ComparativaService

**Archivo a modificar:** `src/services/comparativa.py`

Orquesta los pasos 3 y 4. Maneja errores de red y LLM convirtiéndolos en respuestas con `status="error"` en lugar de propagar excepciones HTTP (eso lo hace el endpoint).

```python
from loguru import logger

from src.config.settings import get_settings
from src.schemas.comparativa import ComparativaResponse
from src.utils.llm import analyze_cv_match
from src.utils.scraping import fetch_job_description


class ComparativaService:
    """Orquesta el pipeline de comparativa CV-oferta laboral."""

    @staticmethod
    async def comparar(
        job_url: str,
        cv_content: str,
        cv_filename: str,
    ) -> ComparativaResponse:
        """Ejecuta el pipeline completo: scraping → LLM → respuesta estructurada.

        Args:
            job_url: URL pública de la oferta laboral.
            cv_content: Contenido del CV en Markdown.
            cv_filename: Nombre original del archivo CV.

        Returns:
            ComparativaResponse con el análisis completo o un mensaje de error.
        """
        settings = get_settings()
        logger.info(f"BL > ComparativaService.comparar() - Iniciando pipeline | url={job_url}")

        try:
            job_description = await fetch_job_description(
                url=job_url,
                timeout=settings.scraping_timeout_seconds,
            )
            result = await analyze_cv_match(
                cv_content=cv_content,
                job_description=job_description,
                api_key=settings.llm_api_key,
                model=settings.llm_model,
                base_url=settings.llm_base_url,
            )
            logger.info(
                f"BL > ComparativaService.comparar() - Pipeline completado | score={result.match_score}"
            )
            return ComparativaResponse(
                job_url=job_url,
                cv_filename=cv_filename,
                status="completed",
                message=result.summary,
                result=result,
            )
        except Exception as exc:
            logger.error(f"BL > ComparativaService.comparar() - Error en pipeline | {exc}")
            return ComparativaResponse(
                job_url=job_url,
                cv_filename=cv_filename,
                status="error",
                message=str(exc),
                result=None,
            )
```

> El endpoint `src/api/endpoints/comparativa.py` **no cambia**.

---

### Paso 6 — Tests

**Directorio:** `tests/` (crear subdirectorios `unit/` e `integration/`)

> **Dependencias nuevas requeridas para dev:** `pytest`, `pytest-asyncio`, `pytest-cov`, `httpx` (para `TestClient` de FastAPI).

| Test | Archivo | Tipo | Qué mockear |
|---|---|---|---|
| `test_validate_url` | `tests/unit/test_comparativa_endpoint.py` | Unit | Nada |
| `test_file_size_limit` | `tests/unit/test_comparativa_endpoint.py` | Unit | Nada |
| `test_fetch_job_description_ok` | `tests/unit/test_scraping.py` | Unit | `httpx.AsyncClient` |
| `test_fetch_job_description_timeout` | `tests/unit/test_scraping.py` | Unit | `httpx.AsyncClient` |
| `test_analyze_cv_match_ok` | `tests/unit/test_llm.py` | Unit | `openai.AsyncOpenAI` |
| `test_analyze_cv_match_bad_json` | `tests/unit/test_llm.py` | Unit | `openai.AsyncOpenAI` |
| `test_comparar_pipeline_ok` | `tests/unit/test_comparativa_service.py` | Unit | `fetch_job_description` + `analyze_cv_match` |
| `test_comparar_pipeline_scraping_error` | `tests/unit/test_comparativa_service.py` | Unit | `fetch_job_description` lanza excepción |
| `test_post_comparativa_full` | `tests/integration/test_comparativa_api.py` | Integration | `ComparativaService.comparar` |

Los tests de integración usan `httpx.AsyncClient` con `app` de FastAPI directamente (sin servidor real). `ComparativaService` se mockea en integration para evitar llamadas externas en CI.

---

## Risk Assessment

### Scraping frágil (ALTO)

LinkedIn, Greenhouse, Lever y la mayoría de job boards bloquean scrapers con rate limiting, captchas o JS rendering. `beautifulsoup4` solo funciona con HTML estático.

- **Corto plazo:** implementar con `httpx` + `beautifulsoup4` para URLs simples (job boards con HTML estático). Documentar que LinkedIn no está soportado.
- **Medio plazo:** si el target principal es LinkedIn, evaluar `playwright` (async, headless) o la LinkedIn Jobs API. El cambio queda aislado en `src/utils/scraping.py` — el resto del pipeline no cambia.

### Latencia del LLM (MEDIO)

Una llamada a GPT-4o-mini tarda 3-10 segundos. El endpoint actual es síncrono desde la perspectiva del usuario.

- **Corto plazo:** mantener la llamada async dentro del event loop de FastAPI — no bloquea otros requests concurrentes.
- **Medio plazo:** si se necesita feedback en tiempo real, convertir a patrón job-queue: POST devuelve un `job_id`, GET `/comparativa/{job_id}` retorna el resultado. Requiere Redis + ARQ — justificado solo con usuarios concurrentes reales.

### LLM no retorna JSON válido (MEDIO)

Los modelos pueden alucinar estructura o romper el JSON.

- **Mitigación:** usar `response_format={"type": "json_object"}` (OpenAI) o structured outputs con el schema de `ComparativaResult`. Añadir retry con backoff (máximo 2 intentos) antes de devolver error.

### Sin tests al arrancar (BAJO-MEDIO)

`pytest` y `pytest-asyncio` no están en `pyproject.toml`. El comando `poetry run pytest` del `CLAUDE.md` fallará hasta que se añadan.

- **Acción requerida:** añadir manualmente a `[dependency-groups].dev` en `pyproject.toml`: `pytest`, `pytest-asyncio`, `pytest-cov`, `httpx`.

---

## Resumen de dependencias a añadir

| Dependencia | Grupo | Uso |
|---|---|---|
| `pydantic-settings` | main | Cargar `.env` con validación Pydantic |
| `httpx` | main | Cliente HTTP async para scraping |
| `beautifulsoup4` | main | Parsing HTML → texto limpio |
| `openai` | main | SDK LLM (compatible con cualquier provider via `base_url`) |
| `pytest` | dev | Runner de tests |
| `pytest-asyncio` | dev | Soporte async en tests |
| `pytest-cov` | dev | Cobertura de código |
