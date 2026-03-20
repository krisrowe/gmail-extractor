# Gmail Extractor (gmex)

A decoupled toolset for high-speed Gmail extraction and local storage.

## 🚀 Getting Started

### 1. Installation
```bash
make dev
```

### 2. Authentication Handshake
```bash
gwsa token generate custom --scopes mail | gmex token import
```

### 3. Fetching (Local CLI)
```bash
gmex fetch
```

### 4. Fetching (Docker Container)
```bash
make build
make fetch

# With overrides
GMEX_LIMIT=10 GMEX_QUERY="is:unread" make fetch
```

## 📂 Data & Configuration

- **Default Location:** `~/.local/share/email-archive/`
- **Env Overrides:** `EMAIL_ARCHIVE_DATA_DIR`, `GMEX_QUERY`, `GMEX_LIMIT`

## Deploying to GCR

### Cloud Build (recommended)

Builds and pushes the image remotely via Google Cloud Build:

```bash
gcloud builds submit --project=your-project-id
```

This uses `cloudbuild.yaml` to build and publish `gcr.io/your-project-id/gmex-fetcher:latest`.

### Local build + push

Build locally and push directly to GCR:

```bash
docker build -t gmex-fetcher:latest .
docker tag gmex-fetcher:latest gcr.io/your-project-id/gmex-fetcher:latest
docker push gcr.io/your-project-id/gmex-fetcher:latest
```

## Development

- **Unit Tests:** `make test`
- **Integration:** `make test-e2e`
