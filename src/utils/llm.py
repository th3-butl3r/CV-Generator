import json
import re
from typing import Any

import httpx

from config.settings import settings, logger
from schemas.comparativa import ComparativaResult

_MAX_JOB_CHARS = 3000
_MAX_CV_CHARS = 2000
_OPENROUTER_URL = settings.OPENROUTER_URL

_SYSTEM_PROMPT = """Eres un evaluador de candidatos. Compara la oferta laboral con el CV y devuelve un JSON de compatibilidad.

RESPONDE SOLO CON ESTE JSON (sin texto adicional, sin explicaciones):
{
  "match_score": 75,
  "summary": "El candidato tiene experiencia relevante pero le faltan algunas habilidades clave.",
  "strengths": ["Fortaleza 1", "Fortaleza 2"],
  "skill_gaps": [
    {"skill": "Nombre habilidad", "present_in_cv": false, "relevance": "alta"},
    {"skill": "Otra habilidad", "present_in_cv": true, "relevance": "media"}
  ],
  "recommendations": ["Recomendación 1", "Recomendación 2"]
}

Definiciones:
- match_score: entero 0-100, compatibilidad entre el CV y la oferta
- summary: 2-3 oraciones sobre la compatibilidad
- strengths: habilidades del candidato que encajan con la oferta
- skill_gaps: habilidades que pide la oferta, indicando si el candidato las tiene
- recommendations: consejos concretos para mejorar la candidatura"""


def _extract_json(text: str) -> dict[str, Any]:
    """Extrae un objeto JSON del texto, tolerando bloques markdown y texto extra."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        return json.loads(match.group(1))

    start, end = text.find("{"), text.rfind("}") + 1
    if start != -1 and end > start:
        return json.loads(text[start:end])

    raise ValueError(f"No se encontró JSON válido en la respuesta: {text[:300]}")


async def analyze_cv_match(
    cv_content: str,
    job_description: str,
    model: str,
    api_key: str,
) -> ComparativaResult:
    """Llama a OpenRouter para analizar la coincidencia CV-oferta.

    Args:
        cv_content: Contenido del CV en formato Markdown.
        job_description: Texto limpio de la oferta laboral.
        model: ID del modelo OpenRouter a usar.
        api_key: API key de OpenRouter.

    Returns:
        ComparativaResult con score, skills y recomendaciones.

    Raises:
        RuntimeError: Si el LLM no retorna JSON parseable tras los reintentos.
    """
    logger.info(f"BL > analyze_cv_match() - Llamando OpenRouter | model={model}")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    user_message = (
        f"Oferta laboral:\n{job_description[:_MAX_JOB_CHARS]}\n\n"
        f"CV del candidato:\n{cv_content[:_MAX_CV_CHARS]}\n\n"
        "Devuelve el JSON de compatibilidad."
    )
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    }

    last_error: Exception | None = None
    for attempt in range(1, 3):
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    _OPENROUTER_URL, headers=headers, json=payload
                )
                response.raise_for_status()

            raw = response.json()["choices"][0]["message"]["content"] or ""
            data = _extract_json(raw)
            result = ComparativaResult(**data)
            logger.info(
                f"BL > analyze_cv_match() - Análisis completado | score={result.match_score}"
            )
            return result
        except Exception as exc:
            logger.warning(
                f"BL > analyze_cv_match() - Error en intento {attempt} | {exc}"
            )
            last_error = exc

    raise RuntimeError(
        f"El LLM no retornó un resultado válido tras 2 intentos: {last_error}"
    )
