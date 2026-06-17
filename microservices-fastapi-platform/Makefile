.DEFAULT_GOAL := help
COMPOSE := docker compose
SERVICES := api-gateway user-service data-service

.PHONY: help up down build logs ps lint test fmt migrate clean load hooks

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

up: ## Start the full stack (build + run, detached)
	$(COMPOSE) up --build -d

down: ## Stop the stack
	$(COMPOSE) down

build: ## Build all images
	$(COMPOSE) build

logs: ## Tail logs from all services
	$(COMPOSE) logs -f

ps: ## Show running containers
	$(COMPOSE) ps

lint: ## Run ruff across all services
	ruff check services/

fmt: ## Auto-format with ruff
	ruff check --fix services/
	ruff format services/

test: ## Run the test suite for every service
	@for svc in $(SERVICES); do \
		echo "== $$svc =="; \
		( cd services/$$svc && pytest tests/ -q ) || exit 1; \
	done

migrate: ## Apply DB migrations inside the running containers
	$(COMPOSE) exec user-service alembic upgrade head
	$(COMPOSE) exec data-service alembic upgrade head

load: ## Run the k6 load test against the gateway (needs the stack up)
	k6 run load/k6-smoke.js

hooks: ## Install the pre-commit hooks locally
	pre-commit install

clean: ## Stop the stack and drop volumes
	$(COMPOSE) down -v
