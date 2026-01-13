.PHONY: test test-archive test-e2e dev build fetch

dev:
	pip install -e ./email-archive -e ./gmex-sdk -e ./gmex-cli

test:
	PYTHONPATH=email-archive/src pytest -s --log-cli-level=INFO email-archive/tests

build:
	docker build -t gmex-fetcher:latest .

fetch:
	@export GMEX_ENV=$$(PYTHONPATH=gmex-sdk/src:email-archive/src python3 -m gmex_sdk.paths); \
	eval $$GMEX_ENV; \
	docker run --rm \
	  --user $$(id -u):$$(id -g) \
	  -v $$EMAIL_ARCHIVE_DATA_DIR:/data \
	  -v $$GOOGLE_APPLICATION_CREDENTIALS:/app/creds.json:ro \
	  -e EMAIL_ARCHIVE_DATA_DIR=/data \
	  -e GOOGLE_APPLICATION_CREDENTIALS=/app/creds.json \
	  -e GMEX_QUERY \
	  -e GMEX_LIMIT \
	  gmex-fetcher:latest

test-e2e: build
	python3 scripts/test_docker_e2e.py
