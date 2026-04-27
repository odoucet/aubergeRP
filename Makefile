# ─── Paths ────────────────────────────────────────────────────────────────────
DOCKER_DIR       := docker
PROFILES_DIR     := $(DOCKER_DIR)/profiles
MODELFILES_DIR   := $(DOCKER_DIR)/modelfiles
MODELS_DIR       := data/models
COMPOSE_BASE     := $(DOCKER_DIR)/docker-compose.yml
OLLAMA_CONTAINER := auberge-ai

# ─── Profile detection ────────────────────────────────────────────────────────
AVAILABLE_PROFILES := $(patsubst $(PROFILES_DIR)/%.yml,%,$(wildcard $(PROFILES_DIR)/*.yml))
# Supports both: make docker rtx3090  and  make docker PROFILE=rtx3090
PROFILE ?= $(word 2,$(MAKECMDGOALS))

# ─── Per-profile model specs ──────────────────────────────────────────────────
RTX3090_LLM_REPO := unsloth/GLM-4.7-Flash-GGUF
RTX3090_LLM_FILE := GLM-4.7-Flash-Q4_0.gguf
RTX3090_LLM_NAME := glm47-flash:q4_0
RTX3090_LLM_MF   := glm47flash.Modelfile

RTX3090_IMG_REPO := unsloth/FLUX.2-klein-9B-GGUF
RTX3090_IMG_FILE := FLUX.2-klein-9B-Q4_K_M.gguf
RTX3090_IMG_NAME := flux-klein:9b-q4km
RTX3090_IMG_MF   := flux-klein.Modelfile

# ─── Terminal colours ─────────────────────────────────────────────────────────
GREEN  := \033[1;32m
YELLOW := \033[1;33m
BLUE   := \033[1;34m
RED    := \033[1;31m
RESET  := \033[0m

.PHONY: run test lint help \
        docker stop clean logs \
        _compose-up _download-gguf _ollama-create _setup-rtx3090 \
        $(AVAILABLE_PROFILES)

# ─── Help ─────────────────────────────────────────────────────────────────────
help:
	@printf "$(BLUE)aubergeRP$(RESET) — available commands\n\n"
	@printf "  $(YELLOW)Development$(RESET)\n"
	@printf "    make run              Start dev server (hot-reload, port 8000)\n"
	@printf "    make test             Run test suite\n"
	@printf "    make lint             Run ruff + mypy\n"
	@printf "\n"
	@printf "  $(YELLOW)Docker stack$(RESET)\n"
	@printf "    make docker <profile> Download models, start Ollama + auberge-app\n"
	@printf "    make stop             Stop running containers\n"
	@printf "    make clean            Stop and remove containers and networks\n"
	@printf "    make logs             Tail container logs\n"
	@printf "\n"
	@printf "  $(YELLOW)Available profiles$(RESET)\n"
	@for p in $(AVAILABLE_PROFILES); do \
		printf "    make docker $$p\n"; \
	done
	@printf "\n"
	@printf "  $(YELLOW)Examples$(RESET)\n"
	@printf "    make docker rtx3090\n"
	@printf "    make docker PROFILE=rtx3090\n"

# ─── Dev targets ──────────────────────────────────────────────────────────────
run:
	python -m uvicorn aubergeRP.main:app --reload --host 0.0.0.0 --port 8000

test:
	python -m pytest tests/

lint:
	python -m ruff check aubergeRP/ tests/
	python -m mypy aubergeRP/

# ─── Docker: make docker <profile> ────────────────────────────────────────────
docker:
	@if [ -z "$(PROFILE)" ]; then \
		printf "$(RED)Error:$(RESET) No profile specified.\n"; \
		printf "Usage:  make docker <profile>\n"; \
		printf "Profiles: $(AVAILABLE_PROFILES)\n"; \
		exit 1; \
	fi
	@if [ ! -f "$(PROFILES_DIR)/$(PROFILE).yml" ]; then \
		printf "$(RED)Error:$(RESET) Profile '$(PROFILE)' does not exist.\n"; \
		printf "Profiles: $(AVAILABLE_PROFILES)\n"; \
		exit 1; \
	fi
	@$(MAKE) --no-print-directory _setup-$(PROFILE)

# Absorb hardware names as no-op targets so make doesn't error on them
$(AVAILABLE_PROFILES):
	@:

stop:
	@printf "  $(YELLOW)→$(RESET) Stopping stack...\n"
	@docker compose -f $(COMPOSE_BASE) stop

clean:
	@printf "  $(RED)→$(RESET) Removing containers and networks...\n"
	@docker compose -f $(COMPOSE_BASE) down

logs:
	@docker compose -f $(COMPOSE_BASE) logs -f

# ─── Internal: compose up ─────────────────────────────────────────────────────
_compose-up:
	@printf "  $(BLUE)→$(RESET) Starting stack [$(PROFILE)]...\n"
	@docker compose \
		-f $(COMPOSE_BASE) \
		-f $(PROFILES_DIR)/$(PROFILE).yml \
		up -d --remove-orphans

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

# ─── RTX 3090 ─────────────────────────────────────────────────────────────────
_setup-rtx3090:
	@$(MAKE) --no-print-directory _download-gguf FILE=$(RTX3090_LLM_FILE) REPO=$(RTX3090_LLM_REPO)
	@$(MAKE) --no-print-directory _download-gguf FILE=$(RTX3090_IMG_FILE) REPO=$(RTX3090_IMG_REPO)
	@$(MAKE) --no-print-directory _compose-up    PROFILE=rtx3090
	@$(MAKE) --no-print-directory _ollama-create NAME=$(RTX3090_LLM_NAME) MODELFILE=$(RTX3090_LLM_MF)
	@$(MAKE) --no-print-directory _ollama-create NAME=$(RTX3090_IMG_NAME) MODELFILE=$(RTX3090_IMG_MF)
