.PHONY: test test-archive test-gmex test-e2e install dev deploy-local

# Install all packages in editable mode
dev:
	pip install -e ./email-archive -e ./gmex-sdk -e ./gmex-cli

# Run all tests
test: test-archive test-gmex

# Run archive tests
test-archive:
	PYTHONPATH=email-archive/src pytest -s --log-cli-level=INFO email-archive/tests

# Run gmex tests (to be implemented)
test-gmex:
	@echo "Running gmex tests..."
	@echo "No tests implemented for gmex-sdk or gmex-cli yet."

# Run End-to-End Docker Test
test-e2e:
	@echo "Running E2E integration test..."
	python3 scripts/test_docker_e2e.py

# Run local deployment via Docker Compose
deploy-local:
	@if [ -z "$(DATA_DIR)" ]; then \
		echo "Error: DATA_DIR env var required (e.g., make deploy-local DATA_DIR=/tmp/emails)"; \
		exit 1; \
	fi
	@echo "Deploying locally with data at: $(DATA_DIR)"
	DATA_DIR=$(DATA_DIR) docker compose up -d --build
	@echo "Fetcher service started. Logs:"
	DATA_DIR=$(DATA_DIR) docker compose logs -f