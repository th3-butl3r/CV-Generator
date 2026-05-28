import re

import markdown
import weasyprint

from config.settings import logger, settings
from utils.cv_llm import generate_markdown_cv
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
            model=settings.LLM_MODEL,
            host=settings.OLLAMA_HOST,
        )

        body_html = markdown.markdown(
            cv_markdown,
            extensions=["extra", "nl2br"],
        )

        css = _extract_css(template_name)
        full_html = _build_html(css, body_html)

        logger.info("BL > CVGeneratorService.generate() - Renderizando PDF")
        pdf = weasyprint.HTML(string=full_html).write_pdf()

        logger.info(f"BL > CVGeneratorService.generate() - PDF listo | bytes={len(pdf)}")
        return pdf
