# Backend — Plan de Fases de Implementación

- **Date**: 2026-05-23
- **Status**: Proposed
- **Scope**: `src/config/`, `src/schemas/`, `src/utils/`, `src/services/`, `tests/`
- **Spec de referencia**: `00_implementacion_nucleo_comparativa.md`

---

## Estado actual

`ComparativaService.comparar()` devuelve un stub con `status="pending"`. El pipeline
real — scraping de la oferta laboral, parsing del texto, análisis LLM, respuesta
estructurada — no existe. Los módulos de soporte (`config/`, `utils/`) están vacíos.
No hay dependencias de HTTP client, LLM client ni scraping en `pyproject.toml`. No hay
tests.

---

## Target state

Un pipeline completamente async con tres capas bien separadas:

```
Endpoint → ComparativaService → [ScrapingClient + LLMClient] → ComparativaResponse (enriquecido)
                                        ↑
                               src/config/settings.py (pydantic-settings)
```

---

## Dependencias nuevas requeridas

Añadir manualmente a `pyproject.toml` antes de empezar las fases de implementación.

| Dependencia | Grupo | Motivo |
|---|---|---|
| `httpx` | main | Cliente HTTP async para llamar a la Jina AI Reader API |
| `openai` | main | SDK LLM compatible con cualquier provider via `base_url` |
| `pytest` | dev | Runner de tests |
| `pytest-asyncio` | dev | Soporte async en tests |
| `pytest-cov` | dev | Cobertura de código |

> `pydantic-settings` y `python-dotenv` ya están instalados (`src/config/settings.py` los usa).
> `beautifulsoup4` **no se necesita**: el texto limpio lo entrega Jina AI Reader directamente.

---

## Fase 1 — Preparación del entorno

**Objetivo**: asegurar que el entorno de ejecución y desarrollo está listo antes de
escribir código funcional. Sin esta fase, las fases siguientes no arrancan.

### 1.1 — Variables de entorno

`src/config/.env` ya existe con `ENVIRONMENT`, `PYTHONPATH` y `LOCAL_JINA_AI`.
Añadir las variables LLM siguiendo el mismo patrón `{ENVIRONMENT}_*`:

```dotenv
# Variables ya existentes (no tocar)
PYTHONPATH="src"
ENVIRONMENT="LOCAL"
LOCAL_JINA_AI="<key ya presente>"

# Añadir: variables LLM por entorno
LOCAL_LLM_API_KEY=<tu-api-key>
LOCAL_LLM_MODEL=gpt-4o-mini
LOCAL_LLM_BASE_URL=https://api.openai.com/v1
LOCAL_LLM_TIMEOUT_SECONDS=30
```

> El patrón `{ENVIRONMENT}_*` permite tener valores distintos para `LOCAL`, `DEVELOPMENT`
> y `PRODUCTION` sin cambiar código — solo cambia `ENVIRONMENT` en el entorno de
> despliegue.

### 1.2 — Añadir dependencias

Ejecutar tras actualizar `pyproject.toml` manualmente:

```bash
poetry install
```

### 1.3 — Verificar arranque

```bash
poetry run uvicorn main:app --reload
```

El servidor debe arrancar sin errores de importación.

### Criterio de aceptación

- `poetry install` termina sin errores.
- `poetry run uvicorn main:app --reload` arranca.
- `src/config/.env` existe localmente y está en `.gitignore`.

---

## Fase 2 — Configuración centralizada

**Objetivo**: extender `BaseConfig` en `src/config/settings.py` para incluir las
variables LLM, respetando el patrón `{ENVIRONMENT}_*` ya establecido en el proyecto.
No se reescribe el módulo — se añaden campos a la clase existente.

**Archivo a modificar:** `src/config/settings.py`

El archivo actual ya carga `JINA_AI` con el patrón `env_file[f"{ENVIRONMENT}_JINA_AI"]`.
Hay que añadir los campos LLM siguiendo exactamente el mismo patrón:

- Leer `ENVIRONMENT` del `.env`
- Acceder a `env_file[f"{ENVIRONMENT}_LLM_API_KEY"]`, etc.
- Añadir `jina_timeout_seconds` e `llm_timeout_seconds` con valores por defecto

Los nuevos campos a añadir a `BaseConfig`:

| Campo en Settings | Variable en .env (LOCAL) | Valor por defecto |
|---|---|---|
| `JINA_AI` | `LOCAL_JINA_AI` | — (ya existe) |
| `LLM_API_KEY` | `LOCAL_LLM_API_KEY` | — (requerido) |
| `LLM_MODEL` | `LOCAL_LLM_MODEL` | `"gpt-4o-mini"` |
| `LLM_BASE_URL` | `LOCAL_LLM_BASE_URL` | `"https://api.openai.com/v1"` |
| `LLM_TIMEOUT_SECONDS` | `LOCAL_LLM_TIMEOUT_SECONDS` | `30` |
| `JINA_TIMEOUT_SECONDS` | `LOCAL_JINA_TIMEOUT_SECONDS` | `15` |

**Archivo a modificar:** `src/config/__init__.py`

Exportar `settings` (el singleton ya instanciado al final del módulo) para que el
resto del proyecto lo importe desde un único punto:

```python
from src.config.settings import settings

__all__ = ["settings"]
```

### Criterio de aceptación

- `from src.config import settings` funciona sin errores.
- `settings.JINA_AI` devuelve la key ya presente en `.env`.
- `settings.LLM_API_KEY` devuelve la key añadida en Fase 1.
- Si falta `LOCAL_LLM_API_KEY` en `.env`, la aplicación falla al arrancar con un
  `KeyError` claro (no en tiempo de ejecución del request).

---

## Fase 3 — Schema enriquecido

**Objetivo**: enriquecer `ComparativaResponse` con los campos que el pipeline LLM
producirá, sin romper el contrato existente del endpoint ni del frontend actual.

**Archivo a modificar:** `src/schemas/comparativa.py`

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
    """Respuesta completa del endpoint /api/v1/comparativa/."""

    job_url: str
    cv_filename: str
    status: str  # "completed" | "error" | "pending"
    message: str
    result: ComparativaResult | None = None
```

El campo `result` es `None` cuando `status="error"` o `status="pending"`, lo que
mantiene compatibilidad con el frontend actual durante la transición.

### Criterio de aceptación

- `ComparativaResponse` importa sin errores.
- Un `ComparativaResponse` con `result=None` serializa correctamente a JSON.
- Un `ComparativaResponse` con `result` poblado serializa con todos los campos de
  `ComparativaResult`.

---

## Fase 4 — Cliente Jina AI Reader

**Objetivo**: dado una URL, obtener el texto limpio de la oferta usando la
[Jina AI Reader API](https://jina.ai/reader/). Responsabilidad única — no interpreta
el contenido.

### Cómo funciona Jina AI Reader

La API convierte cualquier URL en texto Markdown limpio con una sola llamada HTTP:

```
GET https://r.jina.ai/<url-de-la-oferta>
Authorization: Bearer <JINA_AI key>
```

No requiere scraping ni parsing de HTML — Jina AI maneja el rendering de JS, iframes
y estructuras complejas de job boards (incluido LinkedIn). El response es texto plano
listo para enviar al LLM.

**Archivo a crear:** `src/utils/reader.py`

La función `fetch_job_description(url, api_key, timeout) -> str` debe:

- Construir la URL destino: `https://r.jina.ai/{url}`
- Llamar con `httpx.AsyncClient` incluyendo `Authorization: Bearer {api_key}`
- Manejar `httpx.TimeoutException` → `ValueError`
- Manejar `httpx.HTTPStatusError` (4xx/5xx) → `ValueError`
- Validar que el texto retornado no esté vacío → `ValueError`
- Retornar el texto limpio

### Notas de diseño

- Al usar Jina AI Reader se elimina `beautifulsoup4` como dependencia.
- La key (`JINA_AI` en `settings`) ya existe en `.env` — no hay que gestionarla de nuevo.
- Cambio de nombre de módulo: `src/utils/reader.py` en lugar de `scraping.py` para
  reflejar que se usa una API de lectura, no scraping directo.

### Criterio de aceptación

- Dado una URL válida y la key de Jina, retorna texto Markdown no vacío.
- Dado una key inválida, lanza `ValueError` con el código HTTP recibido.
- Dado un timeout superado, lanza `ValueError` con mensaje descriptivo.

---

## Fase 5 — Cliente LLM

**Objetivo**: construir el prompt, llamar al LLM y parsear la respuesta en
`ComparativaResult`. Desacoplado de `ComparativaService` para poder testearlo y
sustituirlo de forma independiente.

**Archivo nuevo:** `src/utils/llm.py`

```python
import json

from loguru import logger
from openai import AsyncOpenAI

from src.schemas.comparativa import ComparativaResult

_SYSTEM_PROMPT = """Eres un experto en selección de personal.
Analiza la coincidencia entre un CV y una oferta laboral.
Devuelve ÚNICAMENTE un objeto JSON con exactamente este schema:
{
  "match_score": <entero 0-100>,
  "summary": "<resumen ejecutivo de 2-3 oraciones>",
  "strengths": ["<fortaleza 1>", "..."],
  "skill_gaps": [
    {"skill": "<nombre>", "present_in_cv": <bool>, "relevance": "<alta|media|baja>"}
  ],
  "recommendations": ["<recomendación 1>", "..."]
}
No incluyas texto fuera del JSON."""


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
        RuntimeError: Si el LLM no retorna JSON parseable tras los reintentos.
    """
    logger.info(f"BL > analyze_cv_match() - Llamando LLM | model={model}")

    client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    user_message = (
        f"## Oferta laboral\n{job_description}\n\n## CV del candidato\n{cv_content}"
    )

    # Intentar hasta 2 veces ante JSON malformado
    last_error: Exception | None = None
    for attempt in range(1, 3):
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
            )
            raw = response.choices[0].message.content or ""
            data = json.loads(raw)
            result = ComparativaResult(**data)
            logger.info(
                f"BL > analyze_cv_match() - LLM respondió | score={result.match_score}"
            )
            return result
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning(
                f"BL > analyze_cv_match() - JSON inválido en intento {attempt} | {exc}"
            )
            last_error = exc

    raise RuntimeError(
        f"El LLM no retornó JSON válido tras 2 intentos: {last_error}"
    )
```

### Decisión de diseño

Usar el SDK `openai` en lugar de `httpx` directo porque:

- Soporte nativo de `response_format={"type": "json_object"}` para forzar JSON.
- Retry automático ante errores de red y rate-limit del proveedor.
- Compatible con cualquier provider OpenAI-compatible (OpenRouter, Groq, Ollama) solo
  cambiando `base_url` + `llm_api_key` en `.env`, sin tocar código.

### Criterio de aceptación

- Dado un mock de `AsyncOpenAI` que retorna JSON válido, retorna `ComparativaResult`.
- Dado un mock que retorna JSON malformado dos veces consecutivas, lanza `RuntimeError`.

---

## Fase 6 — Pipeline ComparativaService

**Objetivo**: orquestar las fases 4 y 5. Manejar errores de red y LLM convirtiéndolos
en respuestas con `status="error"` en lugar de propagar excepciones al endpoint.

**Archivo a modificar:** `src/services/comparativa.py`

```python
from loguru import logger

from src.config import get_settings
from src.schemas.comparativa import ComparativaResponse
from src.utils.llm import analyze_cv_match
from src.utils.reader import fetch_job_description


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
        logger.info(
            f"BL > ComparativaService.comparar() - Iniciando pipeline | url={job_url}"
        )

        try:
            job_description = await fetch_job_description(
                url=job_url,
                api_key=settings.JINA_AI,
                timeout=settings.JINA_TIMEOUT_SECONDS,
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
            logger.error(
                f"BL > ComparativaService.comparar() - Error en pipeline | {exc}"
            )
            return ComparativaResponse(
                job_url=job_url,
                cv_filename=cv_filename,
                status="error",
                message=str(exc),
                result=None,
            )
```

El endpoint `src/api/endpoints/comparativa.py` **no cambia** — la firma de
`ComparativaService.comparar()` se mantiene igual.

### Criterio de aceptación

- Cuando `fetch_job_description` y `analyze_cv_match` tienen éxito, retorna
  `status="completed"` con `result` poblado.
- Cuando `fetch_job_description` lanza una excepción, retorna `status="error"` con
  `result=None` y el mensaje de error en `message`.
- El endpoint no lanza excepciones no controladas.

---

## Fase 7 — Tests

**Objetivo**: cubrir los caminos críticos del pipeline con tests unitarios e de
integración antes de considerar el backend funcional.

**Estructura de directorios:**

```
tests/
├── __init__.py
├── unit/
│   ├── __init__.py
│   ├── test_comparativa_endpoint.py
│   ├── test_reader.py
│   ├── test_llm.py
│   └── test_comparativa_service.py
└── integration/
    ├── __init__.py
    └── test_comparativa_api.py
```

### Tests unitarios

| Test | Archivo | Qué mockear |
|---|---|---|
| `test_validate_url` | `test_comparativa_endpoint.py` | Nada |
| `test_file_size_limit` | `test_comparativa_endpoint.py` | Nada |
| `test_fetch_job_description_ok` | `test_reader.py` | `httpx.AsyncClient` |
| `test_fetch_job_description_timeout` | `test_reader.py` | `httpx.AsyncClient` |
| `test_fetch_job_description_http_error` | `test_reader.py` | `httpx.AsyncClient` |
| `test_analyze_cv_match_ok` | `test_llm.py` | `openai.AsyncOpenAI` |
| `test_analyze_cv_match_bad_json` | `test_llm.py` | `openai.AsyncOpenAI` |
| `test_comparar_pipeline_ok` | `test_comparativa_service.py` | `fetch_job_description` + `analyze_cv_match` |
| `test_comparar_pipeline_scraping_error` | `test_comparativa_service.py` | `fetch_job_description` lanza excepción |
| `test_comparar_pipeline_llm_error` | `test_comparativa_service.py` | `analyze_cv_match` lanza excepción |

### Tests de integración

| Test | Archivo | Qué mockear |
|---|---|---|
| `test_post_comparativa_full` | `test_comparativa_api.py` | `ComparativaService.comparar` |
| `test_post_comparativa_missing_url` | `test_comparativa_api.py` | Nada (validación Pydantic) |
| `test_post_comparativa_invalid_file` | `test_comparativa_api.py` | Nada (validación de extensión) |

Los tests de integración usan `httpx.AsyncClient` con la app FastAPI directamente
(sin servidor real). `ComparativaService` se mockea para evitar llamadas externas en CI.

### Configuración de pytest

Añadir `pytest.ini` o sección `[tool.pytest.ini_options]` en `pyproject.toml`:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

### Criterio de aceptación

- `poetry run pytest --cov=src tests/` pasa sin fallos.
- Cobertura de `src/utils/scraping.py`, `src/utils/llm.py` y
  `src/services/comparativa.py` >= 80%.

---

## Dependencias entre fases

```
Fase 1 (entorno)
  └── Fase 2 (settings)
        └── Fase 3 (schema)    ← puede hacerse en paralelo con Fase 2
              ├── Fase 4 (scraping)
              ├── Fase 5 (llm)
              └── Fase 6 (service) ← requiere Fases 4 y 5 completadas
                    └── Fase 7 (tests)
```

---

## Archivos afectados por fase

| Fase | Archivos a crear / modificar |
|---|---|
| 1 | `src/config/.env` (crear, no commitear) |
| 2 | `src/config/settings.py` (crear), `src/config/__init__.py` (modificar) |
| 3 | `src/schemas/comparativa.py` (modificar) |
| 4 | `src/utils/reader.py` (crear) |
| 5 | `src/utils/llm.py` (crear) |
| 6 | `src/services/comparativa.py` (modificar) |
| 7 | `tests/unit/*.py` (crear), `tests/integration/*.py` (crear) |

---

## Risk assessment

### Jina AI Reader: rate limiting y coste (BAJO-MEDIO)

Jina AI Reader maneja JS rendering, LinkedIn y job boards complejos — elimina el
riesgo de scraping frágil. Sin embargo:

- El plan gratuito tiene límite de requests por día. En uso intensivo puede requerir
  plan de pago.
- Si Jina AI tiene una interrupción de servicio, `fetch_job_description()` falla para
  todas las URLs. El cambio quedaría aislado en `src/utils/reader.py`.
- **Mitigación**: el `ValueError` que lanza la función se captura en
  `ComparativaService` y devuelve `status="error"` con mensaje legible.

### Latencia del LLM (MEDIO)

Una llamada a GPT-4o-mini tarda 3-10 segundos. El endpoint es síncrono desde la
perspectiva del usuario.

- **Corto plazo**: la llamada es async dentro del event loop de FastAPI — no bloquea
  otros requests concurrentes.
- **Medio plazo**: si se necesita feedback en tiempo real, convertir a patrón
  job-queue (POST devuelve `job_id`, GET `/comparativa/{job_id}` retorna resultado).
  Requiere Redis + ARQ — justificado solo con usuarios concurrentes reales.

### LLM no retorna JSON válido (MEDIO)

Los modelos pueden alucinar estructura o romper el JSON.

- **Mitigación**: usar `response_format={"type": "json_object"}` + retry con backoff
  (máximo 2 intentos antes de retornar `status="error"`).

### Sin tests al arrancar (BAJO-MEDIO)

`pytest` y `pytest-asyncio` no están en `pyproject.toml`. El comando
`poetry run pytest` del `CLAUDE.md` fallará hasta que se añadan manualmente.
