# Makefile for Octo-Jules management

.PHONY: help build up start stop restart logs ps clean rebuild

help:
	@echo "Octo-Jules Management Commands:"
	@echo "  make build    - Build or rebuild Docker images"
	@echo "  make up       - Start all services in background"
	@echo "  make rebuild  - Build and start everything (rebuild + up)"
	@echo "  make stop     - Stop all services"
	@echo "  make restart  - Restart all services"
	@echo "  make logs     - View logs for all services (tail)"
	@echo "  make logs-orch - View logs for orchestrator only"
	@echo "  make ps       - Check status of running services"
	@echo "  make clean    - Remove containers and intermediate images"

build:
	docker-compose build

up:
	docker-compose up -d

rebuild: build up

start: up

stop:
	docker-compose down

restart:
	docker-compose restart

logs:
	docker-compose logs -f

logs-orch:
	docker-compose logs -f orchestrator

ps:
	docker-compose ps

clean:
	docker-compose down --rmi all --volumes