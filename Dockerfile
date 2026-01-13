# Multi-Stage Dockerfile for gmail-extractor

# --- Base Stage ---
FROM python:3.11-slim as base
WORKDIR /app

# Install standard dependencies
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Copy the entire monorepo
COPY . .

# Install the internal packages in editable mode for dev parity
RUN pip install -e ./email-archive
RUN pip install -e ./gmex-sdk
RUN pip install -e ./gmex-cli

# --- Fetcher Stage ---
FROM base as fetcher
# Default command (can be overridden)
CMD ["gmex", "fetch"]
