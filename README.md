# Gmail Extractor (gmex)

A decoupled toolset for high-speed Gmail extraction, archiving, and local storage. Optimized for high-volume semantic processing and platform-agnostic archival.

## Architecture

The repository is a monorepo containing three peer packages:
1.  **`email-archive`**: A pure-Python storage SDK using a high-performance two-file strategy (RFC 5322 Headers + JSON Body).
2.  **`gmex-sdk`**: Gmail extraction logic using direct Google APIs (no CLI dependencies).
3.  **`gmex-cli`**: A clean CLI wrapper for syncing and identity management.

---

## 🚀 Getting Started (User Journey)

### 1. Installation
Install all packages in editable mode for local use:
```bash
make dev
```

### 2. Authentication Handshake
`gmex` uses standard Google credentials. We recommend using [gwsa](https://github.com/krisrowe/gworkspace-access) to generate your tokens.

**Generate and Import in one step:**
```bash
# This pipes your secure token directly into gmex configuration
gwsa token generate custom --scopes mail | gmex token import
```

**Verify Identity:**
```bash
gmex token show
```

### 3. Basic Syncing
Sync your inbox to the local archive:
```bash
# Uses internal defaults (in:inbox, limit 50)
gmex sync

# Manual override
gmex sync "from:boss@example.com" --limit 10
```

---

## 📂 Data & Configuration

### Storage Location
By default, emails are stored in your XDG data directory:
`~/.local/share/email-archive/`

Override the location using the standard environment variable:
```bash
export EMAIL_ARCHIVE_DATA_DIR=/path/to/my/archive
```

### Storage Format
- **Metadata (`.meta`)**: RFC 5322 Headers. Optimized for fast scanning and `grep`.
- **Content (`.body`)**: JSON. Contains full body text, HTML, and attachment metadata.
- **Naming**: `[YYYYMMDD-HHMMSS]_[MESSAGE_ID].extension` (Alphabetical = Chronological).

---

## 🐳 Docker Deployment

`gmex` is designed for environment parity between local Docker and Cloud Run Jobs.

### Local "One-Shot" Sync
Run the sync process inside a container using your host's identity:
```bash
make deploy-local DATA_DIR=/path/to/data
```

### Customizing the Job
You can override the search behavior via environment variables:
```bash
GMEX_QUERY="newer_than:7d" GMEX_LIMIT=100 make deploy-local DATA_DIR=/tmp/archive
```

---

## 🛠 SDK Usage (For Developers)

`email-archive` can be used as a standalone library for any email processing task:

```python
from email_archive import EmailStore
from datetime import datetime

store = EmailStore("/path/to/data")

# List emails chronologically
for meta in store.list(since=datetime(2026, 1, 1)):
    # Lazy load only the ones you need
    email = store.get(meta['id'], include_content=True)
    print(f"Subject: {email['subject']}")
    
# Attach processing results (e.g. sidecar metadata)
store.attach(email['id'], "processed.json", {"status": "success"})
```

---

## Development

- **Unit Tests:** `make test`
- **E2E Docker Tests:** `make test-e2e` (Verifies incremental sync and idempotency)
- **Benchmarking:** `python3 email-archive/scripts/performance_test.py`