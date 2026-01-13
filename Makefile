.PHONY: test dev build fetch install

# Install gmex CLI globally via pipx with local dependencies
install:
	@echo "Installing gmex-cli via pipx..."
	pipx install ./gmex-cli --force
	@echo "Injecting local dependencies..."
	pipx runpip gmex-cli install -e ./email-archive -e ./gmex-sdk
	@echo "Done. Run 'gmex --help' to verify."

# Dev setup (editable installs for development)
dev:
	pip install -e ./email-archive -e ./gmex-sdk -e ./gmex-cli

# Run tests
test:
	PYTHONPATH=email-archive/src pytest -s --log-cli-level=INFO email-archive/tests

# Build Docker image
build:
	@if [ "$$VERBOSE" = "1" ]; then \
		echo "Building Docker image..."; \
		docker build -t gmex-fetcher:latest . ; \
	else \
		echo -n "Building Docker image... "; \
		docker build -t gmex-fetcher:latest . > /dev/null 2>&1 || (docker build -t gmex-fetcher:latest . && exit 1); \
		echo "OK."; \
	fi

# Fetch emails using Docker
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
