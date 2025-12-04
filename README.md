# Gmail Extractor (gmex)

Extract Gmail messages to structured formats (CSV, JSON, HTML, TXT).

## Quick Start

```bash
pipx install git+https://github.com/krisrowe/gmail-extractor.git
```

**Prerequisite:** [gwsa](https://github.com/krisrowe/gworkspace-access) must be installed and configured first. See [gwsa setup](#gwsa-setup) below.

After installation, `gmex` is available globally:

```bash
gmex search "label:MyLabel"
gmex prep
gmex fill
gmex readable
```

---

## gwsa Setup

gmex depends on [gwsa](https://github.com/krisrowe/gworkspace-access) for Gmail API access.

**Install gwsa:**
```bash
pipx install git+https://github.com/krisrowe/gworkspace-access.git
```

**Configure authentication:**
1. Create a project in [Google Cloud Console](https://console.cloud.google.com/)
2. Enable the Gmail API
3. Create OAuth 2.0 credentials (Desktop application)
4. Download the credentials JSON and place in `~/.config/gworkspace-access/credentials.json`
5. Run setup and authenticate:
   ```bash
   gwsa setup
   ```
6. Verify:
   ```bash
   gwsa setup --status
   ```

For detailed gwsa configuration, see the [gwsa README](https://github.com/krisrowe/gworkspace-access).

---

## File Naming Convention

gmex uses a prefix-based naming convention:

| File | Description |
|------|-------------|
| `{prefix}_metadata.csv` | Email metadata from search |
| `{prefix}_emails.json` | Full email data with bodies |
| `{prefix}_export.html` | Human-readable HTML export |
| `{prefix}_export.txt` | Plain text export |

Default prefix is `emails` if not specified in config.yaml.

## Configuration (Optional)

You can use gmex in two ways:

### Option 1: Default file names

Without config.yaml, gmex uses `emails` as the default prefix:

```bash
gmex search "label:Important"    # Creates emails_metadata.csv
gmex prep                        # Creates emails_emails.json
gmex fill                        # Populates emails_emails.json
gmex readable                    # Creates emails_export.html, emails_export.txt
```

### Option 2: Using config.yaml

For custom prefixes and repeated use, create a `config.yaml` **in your current working directory**:

```bash
cp /path/to/gmail-extractor/config.yaml.example ./config.yaml
```

Edit `config.yaml`:

```yaml
gmex:
  query: "label:MyLabel"
  file_prefix: myproject
  max_emails: 500
```

**Important:** `config.yaml` must be in the current directory when you run `gmex`.

With config.yaml, commands use your prefix:

```bash
gmex search      # Creates myproject_metadata.csv
gmex prep        # Creates myproject_emails.json
gmex fill        # Populates myproject_emails.json
gmex readable    # Creates myproject_export.html, myproject_export.txt
```

### Specifying files explicitly

You can always specify files explicitly on the command line:

```bash
gmex search "label:Other" other_metadata.csv
gmex prep other_metadata.csv other_emails.json
gmex fill other_emails.json
gmex readable other_emails.json
```

**Command-line arguments always take priority over config values.**

## Commands

### gmex search

Search Gmail and save message metadata to a CSV file.

```bash
gmex search "label:Important"                    # Use default/config prefix
gmex search "label:Important" custom_metadata.csv  # Explicit file name
gmex search --add                                # Add new messages to existing CSV
gmex search --max-results 100                    # Limit results
```

**Safety:** If files already exist, `gmex search` will fail and prompt you to either:
- Archive existing files: `gmex archive`
- Add new messages only: `gmex search --add`

### gmex prep

Convert CSV metadata to JSON with placeholder bodies.

```bash
gmex prep                                        # Use default/config prefix
gmex prep custom_metadata.csv custom_emails.json   # Explicit file names
gmex prep --dry-run                              # Preview changes
```

**Idempotent:** Re-running `gmex prep` will:
- Add new messages from CSV to JSON (preserving existing body data)
- Validate that all JSON message IDs exist in CSV
- Never create duplicates

### gmex fill

Fetch and populate email bodies in the JSON file.

```bash
gmex fill                        # Use default/config prefix
gmex fill custom_emails.json     # Explicit file name
gmex fill -n 3                   # Process only 3 messages (for testing)
gmex fill --dry-run              # Show plan without processing
```

### gmex readable

Export emails to human-readable HTML and TXT files.

```bash
gmex readable                    # Use default/config prefix
gmex readable custom_emails.json # Explicit file name
gmex readable -o custom          # Custom output prefix
```

**Requirement:** All email bodies must be populated before export. If any are pending, the command will fail and tell you to run `gmex fill` first.

### gmex check

Check the status of a JSON file (counts, date range).

```bash
gmex check                       # Use default/config prefix
gmex check custom_emails.json    # Explicit file name
```

### gmex archive

Archive existing gmex files to a timestamped tar.gz file.

```bash
gmex archive                     # Use default/config prefix
gmex archive custom              # Explicit prefix
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

# Option A: Use config.yaml
cp /path/to/gmail-extractor/config.yaml.example ./config.yaml
# Edit config.yaml with your query and prefix

gmex search
gmex prep
gmex fill -n 3      # Test with 3 messages first
gmex check
gmex fill           # Fill remaining
gmex readable

# Option B: Use defaults (no config needed)
gmex search "label:Important"
gmex prep
gmex fill
gmex readable
```

## Shell Scripts (No Installation Required)

If you prefer not to install the CLI, you can use the shell scripts directly.

### Additional Requirements for Shell Scripts

In addition to the Prerequisites above (Python 3.9+, gwsa installed and configured):

- **jq** - JSON processor
  ```bash
  # Ubuntu/Debian
  sudo apt install jq

  # macOS
  brew install jq
  ```

### Setup

```bash
# Clone or navigate to the gmail-extractor directory
cd /path/to/gmail-extractor

# Make scripts executable (one-time setup)
chmod +x *.sh
```

### Quick Start (Shell Scripts)

```bash
cd /path/to/gmail-extractor

# 1. Search Gmail and save metadata to CSV
./search_to_csv.sh "label:MyLabel" my_emails_metadata.csv

# 2. Convert CSV to JSON (with placeholder bodies)
./csv_to_json.sh my_emails_metadata.csv my_emails.json

# 3. Fetch full email bodies from Gmail
./update_bodies.sh my_emails.json

# 4. Check status (optional)
./check_json.sh my_emails.json
```

### Shell Script Reference

#### search_to_csv.sh

Search Gmail and save message metadata to CSV.

```bash
./search_to_csv.sh "<gmail_query>" <output_csv>
```

Example:
```bash
./search_to_csv.sh "label:Important" important_metadata.csv
```

#### csv_to_json.sh

Convert CSV metadata to JSON with placeholder bodies.

```bash
./csv_to_json.sh <input_csv> <output_json>
```

Example:
```bash
./csv_to_json.sh important_metadata.csv important_emails.json
```

#### update_bodies.sh

Fetch and populate email bodies in the JSON file.

```bash
./update_bodies.sh <json_file> [limit]
./update_bodies.sh --dry-run <json_file>    # Preview only
```

Examples:
```bash
./update_bodies.sh important_emails.json      # Process all pending
./update_bodies.sh important_emails.json 3    # Process only 3 (for testing)
./update_bodies.sh --dry-run important_emails.json  # Show plan
```

#### check_json.sh

Check the status of a JSON file.

```bash
./check_json.sh <json_file>
```

Example:
```bash
./check_json.sh important_emails.json
```

### Example Workflow (Shell Scripts)

```bash
cd /path/to/gmail-extractor

# Search and create CSV
./search_to_csv.sh "label:Important" my_emails_metadata.csv

# Convert to JSON
./csv_to_json.sh my_emails_metadata.csv my_emails.json

# Test with a few emails first
./update_bodies.sh my_emails.json 3
./check_json.sh my_emails.json

# Fill remaining emails
./update_bodies.sh my_emails.json

# Verify all bodies are populated
./check_json.sh my_emails.json
```

**Note:** The shell scripts do not include the `readable` export functionality. Use the CLI (`gmex readable`) or process the JSON file with your own tools.
