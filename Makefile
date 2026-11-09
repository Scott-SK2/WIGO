.PHONY: help up down logs api-shell api-test api-lint api-migrate api-seed web-dev web-build schema

help: ## Liste les commandes
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

up: ## Démarre toute la stack (db, redis, api, worker, web)
	docker compose up --build -d

down: ## Arrête la stack
	docker compose down

logs: ## Suit les logs
	docker compose logs -f --tail=100

api-shell: ## Shell Django dans le conteneur api
	docker compose exec api python manage.py shell

api-migrate: ## Applique les migrations
	cd apps/api && uv run python manage.py migrate

api-seed: ## Charge la taxonomie, les communes/quartiers de Bruxelles et des événements de démo
	cd apps/api && uv run python manage.py seed_demo

api-test: ## Lance les tests de l'API
	cd apps/api && uv run pytest

api-lint: ## Lint + format check de l'API
	cd apps/api && uv run ruff check . && uv run ruff format --check .

schema: ## Régénère l'OpenAPI et le client TypeScript
	cd apps/api && uv run python manage.py spectacular --file ../../packages/shared/openapi.yaml --validate
	pnpm gen:api

web-dev: ## Serveur de dev Next.js
	pnpm dev:web

web-build: ## Build de production du web
	pnpm build:web
