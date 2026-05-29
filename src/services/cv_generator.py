import re

import markdown
import weasyprint

from config.settings import logger, settings
from utils.cv_llm import generate_cv_advice, generate_markdown_cv
from utils.reader import fetch_job_description

_TEMPLATES_DIR = "src/web/templates"
_STYLE_RE = re.compile(r"<style>(.*?)</style>", re.DOTALL)


def _extract_css(template_name: str) -> str:
    """Extrae el bloque <style> del archivo de plantilla."""
    path = f"{_TEMPLATES_DIR}/{template_name}.html"
    with open(path, encoding="utf-8") as f:
        html = f.read()
    match = _STYLE_RE.search(html)
    return match.group(1) if match else ""


def _build_html(css: str, body_html: str) -> str:
    return (
        "<!DOCTYPE html><html lang='es'><head>"
        "<meta charset='UTF-8'/>"
        f"<style>{css}</style>"
        "</head>"
        f"<body>{body_html}</body></html>"
    )


class CVAdvisorService:
    """Orquesta el pipeline: Jina → LLM → consejos en Markdown."""

    @staticmethod
    async def analyze(
        job_url: str,
        cv_content: str,
    ) -> str:
        """Analiza el CV frente a una oferta y retorna consejos de optimización.

        Args:
            job_url: URL pública de la oferta laboral.
            cv_content: Contenido del CV base en Markdown.

        Returns:
            String con los consejos en formato Markdown.
        """
        logger.info(f"BL > CVAdvisorService.analyze() - Iniciando | url={job_url}")

        job_description = await fetch_job_description(
            url=job_url,
            api_key=settings.JINA_AI,
            timeout=settings.JINA_TIMEOUT_SECONDS,
        )

        advice = await generate_cv_advice(
            cv_content=cv_content,
            job_description=job_description,
            model=settings.OPENROUTER_MODEL,
            api_key=settings.OPENROUTER_API_KEY,
        )

        logger.info(
            f"BL > CVAdvisorService.analyze() - Análisis listo | chars={len(advice)}"
        )
        return advice


class CVGeneratorService:
    """Orquesta el pipeline: Jina → LLM (Markdown) → HTML → PDF."""

    @staticmethod
    async def generate(
        job_url: str,
        cv_content: str,
        template_name: str,
    ) -> bytes:
        """Genera un CV en PDF a partir del CV base y la oferta laboral.

        Args:
            job_url: URL pública de la oferta laboral.
            cv_content: Contenido del CV base en Markdown.
            template_name: Nombre de la plantilla a usar (sin extensión).

        Returns:
            Bytes del PDF generado.
        """
        logger.info(
            f"BL > CVGeneratorService.generate() - Iniciando | url={job_url} | template={template_name}"
        )

        job_description = await fetch_job_description(
            url=job_url,
            api_key=settings.JINA_AI,
            timeout=settings.JINA_TIMEOUT_SECONDS,
        )

        cv_markdown = await generate_markdown_cv(
            cv_content=cv_content,
            job_description=job_description,
            model=settings.OPENROUTER_MODEL,
            api_key=settings.OPENROUTER_API_KEY,
        )

        body_html = markdown.markdown(cv_markdown, extensions=["extra", "nl2br"])
        css = _extract_css(template_name)
        full_html = _build_html(css, body_html)

        logger.info("BL > CVGeneratorService.generate() - Renderizando PDF")
        pdf = weasyprint.HTML(string=full_html).write_pdf()

        logger.info(f"BL > CVGeneratorService.generate() - PDF listo | bytes={len(pdf)}")
        return pdf
