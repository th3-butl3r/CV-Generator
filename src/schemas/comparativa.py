from pydantic import BaseModel, Field


class SkillGap(BaseModel):
    """Representa una habilidad mencionada en la oferta y su estado en el CV."""

    skill: str
    present_in_cv: bool
    relevance: str = Field(description="alta | media | baja")


class ComparativaResult(BaseModel):
    """Resultado estructurado del análisis LLM."""

    match_score: int = Field(ge=0, le=100)
    summary: str
    strengths: list[str] = Field(default_factory=list)
    skill_gaps: list[SkillGap] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class ComparativaResponse(BaseModel):
    """Schema de respuesta para el endpoint de comparativa."""

    job_url: str
    cv_filename: str
    status: str
    message: str
    result: ComparativaResult | None = None
