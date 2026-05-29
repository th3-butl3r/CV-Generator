from config.settings import logger, settings

from schemas.comparativa import ComparativaResponse
from utils.llm import analyze_cv_match
from utils.reader import fetch_job_description

_INTERNAL_ERROR_MSG = "No se pudo procesar la solicitud. Por favor, inténtalo de nuevo."


class ComparativaService:
    """Servicio de lógica de comparativa entre oferta laboral y CV."""

    @staticmethod
    async def comparar(
        job_url: str, cv_content: str, cv_filename: str
    ) -> ComparativaResponse:
        """Ejecuta el pipeline completo: Jina Reader → Ollama → respuesta estructurada.

        Args:
            job_url: URL de la oferta laboral.
            cv_content: Contenido del archivo Markdown del CV.
            cv_filename: Nombre del archivo subido.

        Returns:
            ComparativaResponse con el resultado del análisis o mensaje de error.
        """
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
                model=settings.OPENROUTER_MODEL,
                api_key=settings.OPENROUTER_API_KEY,
            )
        except Exception as exc:
            logger.error(
                f"BL > ComparativaService.comparar() - Error en pipeline | {exc}"
            )
            return ComparativaResponse(
                job_url=job_url,
                cv_filename=cv_filename,
                status="error",
                message=_INTERNAL_ERROR_MSG,
            )

        return ComparativaResponse(
            job_url=job_url,
            cv_filename=cv_filename,
            status="completed",
            message=result.summary,
            result=result,
        )
