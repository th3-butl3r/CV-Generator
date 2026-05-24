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

# La variable de entorno del sistema tiene prioridad — docker-compose puede
# inyectar ENVIRONMENT=DOCKER sin necesidad de modificar el .env
_env = os.getenv("ENVIRONMENT") or env_file["ENVIRONMENT"]


class BaseConfig(BaseSettings):
    """Global configurations."""

    PROJECT_NAME: Optional[str] = "cv-generator"
    API_V1: Optional[str] = "/v1"
    BACKEND_CORS_ORIGINS: Optional[List[AnyHttpUrl]] = []
    ENVIRONMENT: str = _env
    JINA_AI: str = env_file[f"{_env}_JINA_AI"]
    JINA_TIMEOUT_SECONDS: int = int(env_file.get(f"{_env}_JINA_TIMEOUT_SECONDS", "15"))
    LLM_API_KEY: str = env_file.get(f"{_env}_LLM_API_KEY", "ollama")
    LLM_MODEL: str = env_file.get(f"{_env}_LLM_MODEL", "phi3:mini")
    LLM_BASE_URL: str = env_file.get(f"{_env}_LLM_BASE_URL", "http://localhost:11434/v1")
    LLM_TIMEOUT_SECONDS: int = int(env_file.get(f"{_env}_LLM_TIMEOUT_SECONDS", "60"))


logger.remove()  # Elimina cualquier configuración previa por defecto
logger.add(sys.stderr, level="DEBUG")  # Imprime logs en consola
settings = BaseConfig()
