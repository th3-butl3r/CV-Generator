from pydantic import BaseModel


class ComparativaResponse(BaseModel):
    """Schema de respuesta para el endpoint de comparativa."""

    job_url: str
    cv_filename: str
    status: str
    message: str
