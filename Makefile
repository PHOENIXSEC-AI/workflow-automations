.PHONY: help clean clean-docker docker-dev example start stop diagnose

help:
	@echo "Workflow Automation Project Makefile"
	@echo ""
	@echo "Quick Start:"
	@echo "  docker-dev - start development environment (use this for quickstart)"
	@echo "  example - run example workflow"
	@echo ""
	@echo "Docker Commands:"
	@echo "  start - start all services with docker compose"
	@echo "  stop - stop all services"
	@echo "  diagnose - run docker build diagnostics"
	@echo ""
	@echo "Cleaning:"
	@echo "  clean - remove all build artifacts"
	@echo "  clean-docker - stop containers and remove images"

clean:
	rm -fr build/
	rm -fr dist/
	rm -fr *.egg-info
	rm -fr .eggs/
	find . -name '*.pyc' -delete
	find . -name '*.pyo' -delete
	find . -name '*~' -delete
	find . -name '__pycache__' -exec rm -fr {} +
	find . -name '*.so' -delete
	find . -name '.coverage*' -delete
	find . -name 'htmlcov' -exec rm -fr {} +
	find . -name '.pytest_cache' -exec rm -fr {} +
	find . -name '.tox' -exec rm -fr {} +
	find . -name '*.spec' -delete

clean-docker:
	docker compose down -v
	docker rmi phoenixsec/workflow-automation:latest 2>/dev/null || true

start:
	docker compose up -d

stop:
	docker compose down

# Main quickstart target
docker-dev: start
	@echo "Starting development environment..."
	@echo "Once inside the container, you can run your custom commands"
	docker compose exec development bash

# Example workflow
example: start
	docker compose exec development doc-gen --urls https://github.com/nielstron/demjson3

# Run diagnostics
diagnose:
	@echo "Running docker build diagnostics..."
	./build-debug.sh
	@echo ""
	@echo "Checking docker environment..."
	docker version
	@echo ""
	@echo "Checking docker compose environment..."
	docker compose version
