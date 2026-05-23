# Guía del Proyecto (`CLAUDE.md`)


## 📌 Contexto
Esta es una API para la verificación de "coincidencia" entre una oferta laboral y un candidato. También se tiene una interfaz gráfica pero,
es posible usar la API directamente. El servicio esta construido con Python, FastAPI y HTML.

## Proyecto

Python CV generator.

## 🚀 Comandos Clave (Scripts)
- **Correr tests**: `pytest --cov=app tests/`
- **Formato y Lint**: `pre-commit run --all-files`

## 🛠️ Stack y Entorno
- **Python**: 3.12+
- **Gestor de dependencias**: Poetry (`poetry run ...`)
- **Linter/Formatter**: Ruff
- **Frameworks**: FastAPI

## 🛑 Reglas de Trabajo (Workflow)
- **Calidad**: Escribe type hints (módulo `typing`) en todas las funciones.
- **Documentación**: Añade docstrings estilo **Google** en clases y funciones públicas.
- **Pruebas**: Ejecuta `poetry run pytest` antes de proponer cualquier cambio.
- **Respuestas**: Sé conciso. No incluyas explicaciones largas ni introducciones a menos que se te pida.
- **Comentarios**: Añade comentarios en las partes complejas.
- **Logging**: Añade logs en las funciones con el formato: "BL > NAME_FUNCTION() - MESSAGE". Si la función esta dentro de una clase entonces es: "BL > NAME_CLASS.NAME_FUNCTION() - MESSAGE". Usa el módulo `loguru`. Evita usar `print()`.
- **Secrets**: Las credenciales se leen desde variables de entorno (`.env`), dicho archivo en desarrollo local vive dentro de la carpeta config. Nunca expongas tokens ni claves de API en el código fuente.
- **Tipado estático**: Usa `pydantic` para validación de datos en los endpoints.



## 📁 Estructura del proyecto
- `main.py`: La entra del programa, donde arranca todo.
- `docker-compose.yml`: Para correr el proyecto de manera desplegada y que sea posible desplegarlo en un futuro sin ningún problema.

### Backend
- `src/config/`: Lógica de las configuraciones y la carga de las variables de entorno.
- `src/api`: Lógica de los endpoints y las urls (routers).
- `src/api/endpoints`: Endpoints de la API.
- `src/schemas`: Validación del tipo de dato para cada endpoint.
- `src/utils`: Funciones útiles para cualquier contexto. P. ej. conversión de una fecha a string.
- `src/services`: Lógica aplicada a la entrada de los datos de la API, provenientes de los endpoints.
- `tests/`: Pruebas unitarias y de integración.

### Frontend
- `src/web`: Todo lo relacionado a la interfaz gráfica debe de ir aquí.
- `src/web/templates`: Todos los templates para CV que el usuario puede escoger para generar su CV.



## ⚠️ Lo que NUNCA debes hacer
- No instales dependencias globales ni uses `pip install` sin consultar.
- No modifiques los archivos de configuración (`pyproject.toml`). Cuando sea necesario añadir una librería, lo haré yo manualmente.
- Si no estás seguro de una ruta o función, detente y pregunta.
- Jamas exponer variables de entorno.
