.PHONY: up down build test logs prod

up:
	docker compose up --build

down:
	docker compose down

build:
	docker compose build

test:
	./scripts/test.sh

logs:
	docker compose logs -f

prod:
	docker compose -f compose.yml -f compose.prod.yml up --build

