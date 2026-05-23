from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from config.settings import logger
from pydantic import HttpUrl, ValidationError

from schemas.comparativa import ComparativaResponse
from services.comparativa import ComparativaService

router = APIRouter()

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


def _validate_url(url: str) -> None:
    """Valida que la URL sea HTTP/HTTPS válida.

    Args:
        url: String con la URL a validar.

    Raises:
        HTTPException: Si la URL no es válida.
    """
    try:
        HttpUrl(url)
    except ValidationError:
        raise HTTPException(
            status_code=422, detail="La URL de la oferta laboral no es válida."
        )


@router.post(
    "/", response_model=ComparativaResponse, summary="Comparar CV con oferta laboral"
)
async def comparar(
    job_url: str = Form(..., description="URL de la oferta laboral"),
    cv_file: UploadFile = File(
        ..., description="Archivo Markdown con la información del CV"
    ),
) -> ComparativaResponse:
    """Recibe la URL de una oferta laboral y un CV en formato Markdown para analizarlos.

    Args:
        job_url: URL de la oferta laboral.
        cv_file: Archivo `.md` con el CV del candidato.

    Returns:
        ComparativaResponse con el resultado del análisis.

    Raises:
        HTTPException: Si el archivo no es .md, está vacío o supera el tamaño máximo.
    """
    logger.info(
        f"BL > comparar() - Solicitud recibida | job_url={job_url} | archivo={cv_file.filename}"
    )

    _validate_url(job_url)

    filename = cv_file.filename or ""
    if not filename.endswith(".md"):
        logger.warning(
            f"BL > comparar() - Archivo rechazado, extensión inválida: {filename}"
        )
        raise HTTPException(status_code=400, detail="El archivo debe tener extensión .md")

    content = await cv_file.read()

    if not content:
        raise HTTPException(status_code=400, detail="El archivo está vacío.")

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413, detail="El archivo supera el límite de 5 MB."
        )

    cv_text = content.decode("utf-8")
    result = await ComparativaService.comparar(
        job_url=job_url,
        cv_content=cv_text,
        cv_filename=filename,
    )

    logger.info(f"BL > comparar() - Comparativa completada | status={result.status}")
    return result
