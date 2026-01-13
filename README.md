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

## Development

- **Unit Tests:** `make test`
- **Integration:** `make test-e2e`
