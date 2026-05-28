import sys
import os
from typing import List, Optional

from dotenv import dotenv_values
from loguru import logger  # NOQA
from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings


LOCAL_ENV_PATH = "src/config/.env"
DOCKER_ENV_PATH = "config/.env"

env_path = LOCAL_ENV_PATH if os.path.exists(LOCAL_ENV_PATH) else DOCKER_ENV_PATH
env_file = dotenv_values(env_path)

_env = os.getenv("ENVIRONMENT") or env_file["ENVIRONMENT"]


class BaseConfig(BaseSettings):
    """Global configurations."""

    PROJECT_NAME: Optional[str] = "cv-generator"
    API_V1: Optional[str] = "/v1"
    BACKEND_CORS_ORIGINS: Optional[List[AnyHttpUrl]] = []
    ENVIRONMENT: str = _env
    JINA_AI: str = env_file[f"{_env}_JINA_AI"]
    JINA_TIMEOUT_SECONDS: int = int(env_file.get(f"{_env}_JINA_TIMEOUT_SECONDS", "15"))
    OLLAMA_HOST: str = env_file.get(f"{_env}_OLLAMA_HOST", "http://localhost:11434")
    LLM_MODEL: str = env_file.get(f"{_env}_LLM_MODEL", "qwen2.5:1.5b")


logger.remove()  # Elimina cualquier configuración previa por defecto
logger.add(sys.stderr, level="DEBUG")  # Imprime logs en consola
settings = BaseConfig()
