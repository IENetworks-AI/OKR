.PHONY: help up down ps logs clean

help:
	@echo "Targets: up, down, ps, logs, clean"

up:
	docker compose --env-file .env -f docker-compose.yaml up -d

down:
	docker compose --env-file .env -f docker-compose.yaml down

ps:
	docker compose --env-file .env -f docker-compose.yaml ps

logs:
	docker compose --env-file .env -f docker-compose.yaml logs -f --tail=200

clean:
	docker compose --env-file .env -f docker-compose.yaml down -v
