# ===================================================================
# VPN Platform — convenience commands
# ===================================================================

COMPOSE := docker compose
DEV_COMPOSE := $(COMPOSE) -f docker-compose.dev.yml --env-file .env.dev

# -------------------------------------------------------------------
# Production
# -------------------------------------------------------------------

.PHONY: up down logs

up:
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f

# -------------------------------------------------------------------
# Development
# -------------------------------------------------------------------

.PHONY: dev-up dev-down dev-logs dev-build dev-ps dev-db-reset dev-ngrok dev-shell-backend dev-shell-web

dev-up:
	$(DEV_COMPOSE) up -d

dev-down:
	$(DEV_COMPOSE) down

dev-logs:
	$(DEV_COMPOSE) logs -f

dev-build:
	$(DEV_COMPOSE) build

dev-ps:
	$(DEV_COMPOSE) ps

dev-db-reset:
	python scripts/init_dev_db.py --env .env.dev

dev-ngrok:
	@echo "Start ngrok in another terminal: ngrok http 8000"
	@echo "Then run: ./scripts/update_ngrok_webhook.sh"

dev-shell-backend:
	$(DEV_COMPOSE) exec backend_dev bash

dev-shell-web:
	$(DEV_COMPOSE) exec web_dev bash
