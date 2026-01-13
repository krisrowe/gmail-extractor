# Gmail Extractor (gmex)

A decoupled toolset for high-speed Gmail extraction, archiving, and local storage.

## Architecture

The repository is split into two packages:
1.  **`email-archive`**: A generic, high-performance storage SDK using a two-file strategy (RFC 5322 Headers + JSON Body).
2.  **`gmex`**: The CLI tool and extraction SDK that syncs Gmail to the archive.

## Quick Start

### 1. Installation
```bash
make dev
```

### 2. gwsa Setup
`gmex` depends on [gwsa](https://github.com/krisrowe/gworkspace-access) for Gmail API access.

1. **Install gwsa:**
   ```bash
   pipx install git+https://github.com/krisrowe/gworkspace-access.git
   ```
2. **Configure authentication:**
   - Download OAuth 2.0 credentials to `~/.config/gworkspace-access/credentials.json`.
   - Run `gwsa setup`.
   - Verify with `gwsa setup --status`.

### 3. Configuration
Create a `config.yaml` in your working directory:
```yaml
gmex:
  query: "in:inbox"
  limit: 50
```

### 4. Syncing
```bash
gmex sync
```
By default, data is stored in `~/.local/share/email-archive/`. You can override this with the `EMAIL_ARCHIVE_DATA_DIR` environment variable.

## Development & Testing

### Run Unit Tests
```bash
make test
```

### Run with Debug Logs
```bash
make test-debug
```

### Local Docker Run (One-Shot)
To run the fetcher as a one-off job (parity with Cloud Run):
```bash
make deploy-local DATA_DIR=/path/to/your/data
```

## Storage Format

- **Metadata (`.meta`)**: RFC 5322 Headers. Optimized for fast scanning and `grep`.
- **Content (`.body`)**: JSON. Contains full body text, HTML, and attachment metadata.
- **Filename**: `[YYYYMMDD-HHMMSS]_[MESSAGE_ID].extension`