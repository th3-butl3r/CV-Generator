import json
import re
from typing import Any

from loguru import logger
from openai import AsyncOpenAI

from schemas.comparativa import ComparativaResult


_SYSTEM_PROMPT = """Eres un experto en selección de personal. Analiza la coincidencia entre un CV y una oferta laboral.
Devuelve ÚNICAMENTE un objeto JSON con este esquema exacto, sin texto fuera del JSON:
{
  "match_score": <entero 0-100>,
  "summary": "<resumen ejecutivo de 2-3 oraciones>",
  "strengths": ["<fortaleza 1>", "<fortaleza 2>"],
  "skill_gaps": [{"skill": "<nombre>", "present_in_cv": <bool>, "relevance": "<alta|media|baja>"}],
  "recommendations": ["<recomendación 1>", "<recomendación 2>"]
}"""


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
    api_key: str,
    model: str,
    base_url: str,
    timeout: int = 60,
) -> ComparativaResult:
    """Llama al LLM para analizar la coincidencia CV-oferta.

    Args:
        cv_content: Contenido del CV en formato Markdown.
        job_description: Texto limpio de la oferta laboral.
        api_key: Clave de autenticación del proveedor LLM.
        model: Identificador del modelo a usar.
        base_url: URL base de la API del proveedor.
        timeout: Segundos de timeout para la llamada.

    Returns:
        ComparativaResult con score, skills y recomendaciones.

    Raises:
        RuntimeError: Si el LLM no retorna JSON parseable tras los reintentos.
    """
    logger.info(f"BL > analyze_cv_match() - Llamando LLM | model={model}")

    client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=timeout)
    user_message = f"## Oferta laboral\n{job_description}\n\n## CV del candidato\n{cv_content}"

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
                temperature=0.1,
            )
            raw = response.choices[0].message.content or ""
            data = _extract_json(raw)
            result = ComparativaResult(**data)
            logger.info(f"BL > analyze_cv_match() - Análisis completado | score={result.match_score}")
            return result
        except Exception as exc:
            logger.warning(f"BL > analyze_cv_match() - Error en intento {attempt} | {exc}")
            last_error = exc

    raise RuntimeError(f"El LLM no retornó un resultado válido tras 2 intentos: {last_error}")
