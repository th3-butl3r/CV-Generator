from loguru import logger

from src.schemas.comparativa import ComparativaResponse


class ComparativaService:
    """Servicio de lógica de comparativa entre oferta laboral y CV."""

    @staticmethod
    async def comparar(
        job_url: str, cv_content: str, cv_filename: str
    ) -> ComparativaResponse:
        """Ejecuta la comparativa entre la oferta laboral y el CV.

        Args:
            job_url: URL de la oferta laboral.
            cv_content: Contenido del archivo Markdown del CV.
            cv_filename: Nombre del archivo subido.

        Returns:
            ComparativaResponse con el resultado de la comparativa.
        """
        logger.info(
            f"BL > ComparativaService.comparar() - Procesando comparativa para {job_url}"
        )

        # TODO: implementar lógica de comparativa (scraping + análisis con LLM)
        return ComparativaResponse(
            job_url=job_url,
            cv_filename=cv_filename,
            status="pending",
            message="Comparativa recibida. Lógica de análisis pendiente de implementar.",
        )
