# Gmail Extractor (gmex)

Extract Gmail messages to structured formats (CSV, JSON, HTML, TXT).

## Installation

### Prerequisites

1. **Python 3.9+**

2. **gworkspace-access (gwsa)** - Required for Gmail API access:
   ```bash
   pipx install git+https://github.com/krisrowe/gworkspace-access.git
   ```

   After installation, configure authentication:
   - Place your `client_secrets.json` from Google Cloud Console in `~/.config/gworkspace-access/`
   - Run `gwsa setup` and follow the prompts
   - Verify with `gwsa setup --status`

### Install gmex

```bash
pipx install /path/to/gmail-extractor
```

After installation, `gmex` will be available globally from any directory.

## Quick Start

```bash
# 1. Search Gmail and save metadata to CSV
gmex search "label:MyLabel" emails.csv

# 2. Convert CSV to JSON (with placeholder bodies)
gmex prep emails.csv emails.json

# 3. Fetch full email bodies from Gmail
gmex fill emails.json

# 4. Export to human-readable HTML and TXT
gmex readable emails.json
```

## Configuration (Optional)

You can use gmex in two ways:

### Option 1: Command-line arguments only

Specify all arguments directly on the command line:

```bash
gmex search "label:Important" emails.csv
gmex prep emails.csv emails.json
gmex fill emails.json
gmex readable emails.json
```

### Option 2: Using config.yaml

For repeated use with the same settings, create a `config.yaml` **in your current working directory** (the directory where you run `gmex`):

```bash
# Copy the example config to your project directory
cp /path/to/gmail-extractor/config.yaml.example ./config.yaml
```

Edit `config.yaml`:

```yaml
gmex:
  query: "label:MyLabel"
  base_name: emails
  max_results: 500
```

**Important:** `config.yaml` must be in the current directory when you run `gmex`. The tool looks for it in `./config.yaml` relative to where you execute the command.

With config.yaml present, you can omit arguments:

```bash
gmex search      # Uses query and base_name from config
gmex prep        # Uses base_name from config
gmex fill        # Uses base_name from config
gmex readable    # Uses base_name from config
```

### Mixing command-line and config

**Command-line arguments always take priority over config values.** You can use config.yaml as a baseline and override specific values:

```bash
# config.yaml has base_name: emails, but override query:
gmex search "label:Other"              # Creates other results in emails.csv

# Override everything:
gmex search "label:Other" other.csv    # Ignores config entirely for this command
```

## Commands

### gmex search

Search Gmail and save message metadata to a CSV file.

```bash
gmex search "label:Important" important.csv
gmex search "label:Important" important.csv --add   # Add new messages only
gmex search --max-results 100                       # With config.yaml
```

**Safety:** If files already exist, `gmex search` will fail and prompt you to either:
- Archive existing files: `gmex archive <base_name>`
- Add new messages only: `gmex search ... --add`

### gmex prep

Convert CSV metadata to JSON with placeholder bodies.

```bash
gmex prep emails.csv emails.json
gmex prep --dry-run                    # Preview changes (with config.yaml)
```

**Idempotent:** Re-running `gmex prep` will:
- Add new messages from CSV to JSON (preserving existing body data)
- Validate that all JSON message IDs exist in CSV
- Never create duplicates

### gmex fill

Fetch and populate email bodies in the JSON file.

```bash
gmex fill emails.json              # Process all pending messages
gmex fill emails.json -n 3         # Process only 3 messages (for testing)
gmex fill --dry-run                # Show plan without processing
```

### gmex readable

Export emails to human-readable HTML and TXT files.

```bash
gmex readable emails.json                  # Creates emails-export.html and emails-export.txt
gmex readable -o my_export                 # Custom output name (with config.yaml)
```

**Requirement:** All email bodies must be populated before export. If any are pending, the command will fail and tell you to run `gmex fill` first.

### gmex check

Check the status of a JSON file (counts, date range).

```bash
gmex check emails.json
gmex check                         # With config.yaml
```

### gmex archive

Archive existing gmex files to a timestamped tar.gz file.

```bash
gmex archive emails                # Archives emails.csv, emails.json, etc.
gmex archive                       # With config.yaml
```

## Help

Run any command with `--help` for detailed usage:

```bash
gmex --help
gmex search --help
gmex fill --help
```

## Example Workflow

```bash
# Create a project directory
mkdir my-email-project && cd my-email-project

# Copy and edit config
cp /path/to/gmail-extractor/config.yaml.example ./config.yaml
# Edit config.yaml with your query and base_name

# Or specify everything on command line:
gmex search "label:Important" emails.csv
gmex prep emails.csv emails.json

# Test with a few messages first
gmex fill emails.json -n 3

# Check progress
gmex check emails.json

# Fill remaining messages
gmex fill emails.json

# Export to readable formats
gmex readable emails.json
```
