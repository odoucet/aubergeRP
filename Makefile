export UID := $(shell id -u)
export GID := $(shell id -g)

# ─── Paths ────────────────────────────────────────────────────────────────────
DOCKER_DIR       := docker
PROFILES_DIR     := $(DOCKER_DIR)/profiles
MODELS_DIR       := data/models
COMPOSE_BASE     := $(DOCKER_DIR)/docker-compose.yml
COMPOSE_OLLAMA   := $(DOCKER_DIR)/docker-compose.ollama.yml
OLLAMA_CONTAINER := auberge-ai

# ─── Profile detection ────────────────────────────────────────────────────────
AVAILABLE_PROFILES := $(patsubst $(PROFILES_DIR)/%.yml,%,$(wildcard $(PROFILES_DIR)/*.yml))
LEGACY_GPU := $(word 2,$(MAKECMDGOALS))
GPU ?= $(gpu)

compose_args = -f $(COMPOSE_BASE)$(if $(strip $(GPU)), -f $(COMPOSE_OLLAMA) -f $(PROFILES_DIR)/$(GPU).yml)

# Read a value from the x-gguf section of a profile YAML
# Usage: $(call gguf_get,key,profile)
gguf_get = $(shell sed -n 's/^[[:space:]]*$(1)[[:space:]]*:[[:space:]]*//p' $(PROFILES_DIR)/$(2).yml | sed 's/^&[^ ]* //; s/[[:space:]]*#.*//')

# ─── Terminal colours ─────────────────────────────────────────────────────────
GREEN  := \033[1;32m
YELLOW := \033[1;33m
BLUE   := \033[1;34m
RED    := \033[1;31m
RESET  := \033[0m

.PHONY: run test lint lint-fix doc help \
        docker stop clean logs \
	_compose-up _download-gguf _ollama-create \
	$(AVAILABLE_PROFILES)

# ─── Help ─────────────────────────────────────────────────────────────────────
help:
	@printf "$(BLUE)aubergeRP$(RESET) — available commands\n\n"
	@printf "  $(YELLOW)Development$(RESET)\n"
	@printf "    make run              Start dev server (hot-reload, port 8123)\n"
	@printf "    make test             Run test suite\n"
	@printf "    make lint             Run ruff + mypy\n"
	@printf "    make lint-fix         Fix linting issues automatically (ruff --fix)\n"
	@printf "    make doc              Regenerate docs/03-backend-api.md from source\n"
	@printf "\n"
	@printf "  $(YELLOW)Docker stack$(RESET)\n"
	@printf "    make docker           Start auberge-app only\n"
	@printf "    make docker gpu=<profile>\n"
	@printf "                          Start GPU stack (Ollama + models + auberge-app)\n"
	@printf "    make stop [gpu=...]   Stop running containers\n"
	@printf "    make clean [gpu=...]  Stop and remove containers and networks\n"
	@printf "    make logs [gpu=...]   Tail container logs\n"
	@printf "\n"
	@printf "  $(YELLOW)Available profiles$(RESET)\n"
	@for p in $(AVAILABLE_PROFILES); do \
		printf "    make docker gpu=$$p\n"; \
	done
	@printf "\n"
	@printf "  $(YELLOW)Examples$(RESET)\n"
	@printf "    make docker\n"
	@printf "    make docker gpu=rtx3090\n"
	@printf "    make stop gpu=rtx3090\n"
	@printf "    make clean gpu=rtx3090\n"

# ─── Dev targets ──────────────────────────────────────────────────────────────
run:
	python -m uvicorn aubergeRP.main:app --reload --host 0.0.0.0 --port 8123

test:
	python -m pytest tests/

lint:
	python -m ruff check aubergeRP/ tests/
	python -m mypy aubergeRP/

lint-fix:
	python -m ruff check aubergeRP/ tests/ --fix --unsafe-fixes

doc:
	python scripts/generate_api_docs.py

# ─── Docker: make docker [gpu=<profile>] ─────────────────────────────────────
docker:
	@if [ -n "$(LEGACY_GPU)" ]; then \
		printf "$(RED)Error:$(RESET) Positional profiles are no longer supported.\n"; \
		printf "       Use: make docker gpu=$(LEGACY_GPU)\n"; \
		exit 1; \
	fi
	@if [ -n "$(GPU)" ] && [ ! -f "$(PROFILES_DIR)/$(GPU).yml" ]; then \
		printf "$(RED)Error:$(RESET) GPU profile '$(GPU)' does not exist.\n"; \
		printf "Profiles: $(AVAILABLE_PROFILES)\n"; \
		exit 1; \
	fi
	@if [ -n "$(GPU)" ]; then \
		$(MAKE) --no-print-directory _setup-$(GPU) GPU=$(GPU); \
	else \
		$(MAKE) --no-print-directory _compose-up; \
	fi
stop:
	@printf "  $(YELLOW)→$(RESET) Stopping stack...\n"
	@docker compose $(call compose_args) stop

clean:
	@printf "  $(RED)→$(RESET) Removing containers and networks...\n"
	@docker compose $(call compose_args) down

logs:
	@docker compose $(call compose_args) logs -f

# Explicitly reject legacy positional profile usage.
$(AVAILABLE_PROFILES):
	@printf "$(RED)Error:$(RESET) Positional profiles are no longer supported.\n"
	@printf "       Use: make docker gpu=$@\n"
	@exit 1

# ─── Internal: compose up ─────────────────────────────────────────────────────
_compose-up:
	@if [ -n "$(GPU)" ]; then \
		printf "  $(BLUE)→$(RESET) Starting GPU stack [$(GPU)]...\n"; \
	else \
		printf "  $(BLUE)→$(RESET) Starting app-only stack...\n"; \
	fi

	# make sure we have latest images (especially important for Ollama to get latest modelfile changes)
	@docker compose $(call compose_args) pull
	@docker compose $(call compose_args) \
		up -d --remove-orphans --build

# ─── Internal: download a single GGUF if missing ─────────────────────────────
# Usage: $(MAKE) _download-gguf FILE=x.gguf REPO=org/repo
_download-gguf:
	@if [ -f "$(MODELS_DIR)/$(FILE)" ]; then \
		printf "  $(GREEN)✓$(RESET) $(FILE) already present.\n"; \
	else \
		printf "  $(BLUE)↓$(RESET) Downloading $(FILE) (~may take a while)...\n"; \
		mkdir -p $(MODELS_DIR); \
		if command -v hf >/dev/null 2>&1; then \
			hf download $(REPO) $(FILE) --local-dir $(MODELS_DIR); \
		else \
			printf "  $(RED)✗$(RESET) hf not found.\n"; \
			printf "       Install: pip install 'huggingface_hub[cli]'\n"; \
			exit 1; \
		fi; \
	fi

# ─── Internal: create an Ollama model if not already loaded ──────────────────
# Usage: $(MAKE) _ollama-create NAME=model:tag MODELFILE=file.Modelfile
_ollama-create:
	@printf "  $(BLUE)→$(RESET) Waiting for Ollama API...\n"
	@until docker exec $(OLLAMA_CONTAINER) ollama list >/dev/null 2>&1; do sleep 2; done
	@if docker exec $(OLLAMA_CONTAINER) ollama list 2>/dev/null \
			| awk 'NR>1{print $$1}' | grep -qF "$(NAME)"; then \
		printf "  $(GREEN)✓$(RESET) Model $(NAME) already loaded.\n"; \
	else \
		printf "  $(BLUE)→$(RESET) Creating model $(NAME)...\n"; \
		docker exec $(OLLAMA_CONTAINER) ollama create $(NAME) -f /modelfiles/$(MODELFILE); \
		printf "  $(GREEN)✓$(RESET) $(NAME) ready.\n"; \
	fi

# ─── Generic profile setup (reads specs from x-gguf in the profile YAML) ─────
_setup-%:
	@$(MAKE) --no-print-directory _download-gguf \
		FILE=$(call gguf_get,llm_file,$*) REPO=$(call gguf_get,llm_repo,$*)
	@$(MAKE) --no-print-directory _download-gguf \
		FILE=$(call gguf_get,img_file,$*) REPO=$(call gguf_get,img_repo,$*)
	@$(MAKE) --no-print-directory _compose-up GPU=$*
	@$(MAKE) --no-print-directory _ollama-create \
		NAME=$(call gguf_get,llm_name,$*) MODELFILE=$(call gguf_get,llm_modelfile,$*)
	@$(MAKE) --no-print-directory _ollama-create \
		NAME=$(call gguf_get,img_name,$*) MODELFILE=$(call gguf_get,img_modelfile,$*)
