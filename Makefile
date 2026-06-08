# OMEIA — Linux-first operations (authoritative runtime host)
.PHONY: install up start stop test ready logs

ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
export OMEIA_REPO_ROOT := $(ROOT)
export PYTHONPATH := $(ROOT)$(if $(PYTHONPATH),:$(PYTHONPATH),)

install:
	python3 -m pip install -r requirements.txt
	cd web && npm ci

up start:
	./start_linux.sh

stop:
	./scripts/dev/stop_local_docker.sh || true
	-pkill -f 'uvicorn omeia.api.main' || true
	-pkill -f 'vite' || true

test:
	python3 -m pytest tests/ -q

ready:
	@curl -sf http://127.0.0.1:8000/ready | python3 -m json.tool || (echo "API not ready on :8000" && exit 1)

logs:
	docker compose -f infra/compose/docker-compose.yml logs -f --tail=100
