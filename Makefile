ENV_FILE := src/config/.env

# Lee DOCKER_LLM_PROVIDER del .env y elimina comillas
PROVIDER := $(shell grep -E '^DOCKER_LLM_PROVIDER=' $(ENV_FILE) 2>/dev/null \
            | cut -d= -f2 | tr -d '"' | tr -d "'")

.PHONY: up down logs

up:
	@if [ "$(PROVIDER)" = "ollama" ]; then \
		echo "[make] Proveedor: Ollama — arrancando app + ollama"; \
		docker compose --profile ollama up --build; \
	else \
		echo "[make] Proveedor: OpenRouter — arrancando solo app"; \
		docker compose up --build; \
	fi

down:
	docker compose --profile ollama down

logs:
	docker compose --profile ollama logs -f
