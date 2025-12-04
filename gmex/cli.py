"""Gmail Extractor CLI - Main entry point."""

import click
import csv
import json
import subprocess
import sys
import tarfile
from datetime import datetime
from pathlib import Path

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


# File extensions that gmex creates
GMEX_EXTENSIONS = [".csv", ".json", "-export.html", "-export.txt"]

# Config file name
CONFIG_FILE = "config.yaml"


def load_config():
    """Load config from config.yaml in current directory if it exists."""
    config_path = Path(CONFIG_FILE)
    if not config_path.exists():
        return {}

    if not HAS_YAML:
        click.echo("Warning: PyYAML not installed, config.yaml will be ignored.", err=True)
        click.echo("Install with: pip install pyyaml", err=True)
        return {}

    with open(config_path, "r") as f:
        config = yaml.safe_load(f) or {}

    return config.get("gmex", {})


def get_config_value(config, key, default=None):
    """Get a value from config with optional default."""
    return config.get(key, default)


@click.group()
@click.version_option()
@click.pass_context
def cli(ctx):
    """Gmail Extractor (gmex) - Extract Gmail messages to structured formats.

    Workflow:

    \b
      1. gmex search "label:MyLabel" emails.csv   # Search Gmail, save metadata to CSV
      2. gmex prep emails.csv emails.json         # Convert CSV to JSON with placeholder bodies
      3. gmex fill emails.json                    # Fetch full email bodies from Gmail
      4. gmex readable emails.json                # Export to human-readable HTML and TXT

    If you need to start fresh, use 'gmex archive' to backup existing files first.

    Configuration:
      Create a config.yaml file in your working directory to set defaults:

    \b
      gmex:
        query: "label:MyLabel"
        file_prefix: emails
        max_emails: 500
    """
    ctx.ensure_object(dict)
    ctx.obj["config"] = load_config()


def check_gwsa():
    """Check if gwsa is available."""
    try:
        subprocess.run(["gwsa", "setup", "--status"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def get_prefix_from_path(file_path):
    """Extract prefix from a gmex file path."""
    stem = Path(file_path).stem
    # Remove known suffixes to get prefix
    for suffix in ["_metadata", "_emails", "_export"]:
        if stem.endswith(suffix):
            return stem[:-len(suffix)]
    # Handle -export suffix (for html/txt)
    if stem.endswith("-export"):
        return stem[:-7]
    return stem


def find_related_files(file_path):
    """Find all gmex-related files based on a file path or prefix."""
    base = Path(file_path)
    parent = base.parent if base.parent != Path() else Path(".")

    # Get prefix from the file path
    prefix = get_prefix_from_path(file_path)

    related = []
    for pattern in [
        f"{prefix}_metadata.csv",
        f"{prefix}_emails.json",
        f"{prefix}_export.html",
        f"{prefix}_export.txt"
    ]:
        path = parent / pattern
        if path.exists():
            related.append(path)

    return related


def load_csv_ids(csv_path):
    """Load message IDs from a CSV file."""
    ids = set()
    with open(csv_path, "r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            msg_id = row.get("Message ID", "").strip()
            if msg_id:
                ids.add(msg_id)
    return ids


@cli.command()
@click.argument("prefix", required=False)
@click.pass_context
def archive(ctx, prefix):
    """Archive existing gmex files to a tar.gz file.

    PREFIX is the prefix of the files to archive (optional).
    This will archive: {prefix}_metadata.csv, {prefix}_emails.json,
    {prefix}_export.html, {prefix}_export.txt

    Defaults to config.yaml prefix or "emails" if not specified.

    \b
    Example:
      gmex archive myproject  # Archives myproject_metadata.csv, myproject_emails.json, etc.
      gmex archive            # Use config.yaml prefix or default "emails"
    """
    config = ctx.obj.get("config", {})

    # Apply config defaults using prefix (config or default "emails")
    if prefix is None:
        prefix = config.get("file_prefix", "emails")

    # Find all related files
    related = find_related_files(f"{prefix}_metadata.csv")

    if not related:
        click.echo(f"No gmex files found with prefix '{prefix}'.")
        sys.exit(1)

    click.echo(f"Found {len(related)} file(s) to archive:")
    for f in related:
        click.echo(f"  - {f}")

    # Create archive name with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_name = f"{prefix}_archived_{timestamp}.tar.gz"

    click.echo()
    click.echo(f"Creating archive: {archive_name}")

    with tarfile.open(archive_name, "w:gz") as tar:
        for f in related:
            tar.add(f, arcname=f.name)

    # Remove original files
    for f in related:
        f.unlink()
        click.echo(f"  Removed: {f}")

    click.echo()
    click.echo(f"Archive complete: {archive_name}")
    click.echo("You can now run 'gmex search' to start fresh.")


@cli.command()
@click.argument("query", required=False)
@click.argument("output_csv", type=click.Path(), required=False)
@click.option("--max-results", default=None, type=int, help="Maximum number of results to fetch.")
@click.option("--add", is_flag=True, help="Add new messages to existing CSV without duplicates.")
@click.pass_context
def search(ctx, query, output_csv, max_results, add):
    """Search Gmail and save metadata to CSV.

    QUERY is a Gmail search query (e.g., "label:MyLabel", "from:someone@example.com").

    OUTPUT_CSV is the path to the output CSV file.

    Both arguments can be omitted if config.yaml provides defaults.

    \b
    Examples:
      gmex search "label:Important" important.csv
      gmex search "label:Important" important.csv --add   # Add new messages only
      gmex search                                         # Use config.yaml defaults
    """
    config = ctx.obj.get("config", {})

    # Apply config defaults
    if query is None:
        query = config.get("query")
    if max_results is None:
        max_results = config.get("max_emails", 500)

    # Determine output CSV from prefix (config or default "emails")
    if output_csv is None:
        prefix = config.get("file_prefix", "emails")
        output_csv = f"{prefix}_metadata.csv"

    # Validate required args
    if not query:
        click.echo("Error: QUERY is required (or set 'query' in config.yaml).", err=True)
        sys.exit(1)

    if not check_gwsa():
        click.echo("Error: 'gwsa' command not found.", err=True)
        click.echo("Please install gworkspace-access: pipx install git+https://github.com/krisrowe/gworkspace-access.git", err=True)
        sys.exit(1)

    output_path = Path(output_csv)
    related_files = find_related_files(output_csv)

    # Check for existing files
    if related_files and not add:
        click.echo("Error: Existing gmex files found:", err=True)
        for f in related_files:
            click.echo(f"  - {f}", err=True)
        click.echo(err=True)
        click.echo("Options:", err=True)
        click.echo(f"  1. Archive existing files first: gmex archive {output_path.stem}", err=True)
        click.echo(f"  2. Add new messages only: gmex search \"{query}\" {output_csv} --add", err=True)
        sys.exit(1)

    # Load existing IDs if adding
    existing_ids = set()
    if add and output_path.exists():
        existing_ids = load_csv_ids(output_path)
        click.echo(f"Found {len(existing_ids)} existing messages in CSV.")

    click.echo(f"Searching Gmail with query: {query}")

    # Fetch search results
    click.echo(f"Fetching search results from Gmail (up to {max_results})...")
    result = subprocess.run(
        ["gwsa", "mail", "search", query, "--max-results", str(max_results)],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        click.echo(f"Error searching Gmail: {result.stderr}", err=True)
        sys.exit(1)

    try:
        search_results = json.loads(result.stdout)
    except json.JSONDecodeError:
        click.echo("Error: Failed to parse search results.", err=True)
        sys.exit(1)

    if not search_results:
        click.echo(f"No messages found for the query: {query}")
        sys.exit(0)

    click.echo(f"Found {len(search_results)} messages from Gmail.")

    # Filter out existing IDs if adding
    if add:
        new_results = [msg for msg in search_results if msg.get("id") not in existing_ids]
        click.echo(f"New messages to add: {len(new_results)}")
        if not new_results:
            click.echo("No new messages to add.")
            return
        search_results = new_results

    # Sort by date (newest first)
    from email.utils import parsedate_to_datetime

    def parse_date(msg):
        try:
            return parsedate_to_datetime(msg.get("date", ""))
        except:
            return None

    search_results = sorted(search_results, key=lambda x: parse_date(x) or "", reverse=True)

    # Write CSV
    mode = "a" if add and output_path.exists() else "w"
    write_header = not (add and output_path.exists())

    with open(output_csv, mode, newline="") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(["Date", "Message ID", "Thread ID", "From", "To", "Subject"])
        for msg in search_results:
            subject = msg.get("subject", "")
            if subject == "N/A":
                subject = ""
            writer.writerow([
                msg.get("date", ""),
                msg.get("id", ""),
                msg.get("threadId", ""),
                msg.get("from", ""),
                msg.get("to", ""),
                subject
            ])

    click.echo()
    if add:
        total_ids = load_csv_ids(output_path)
        click.echo(f"Added {len(search_results)} new messages.")
        click.echo(f"Total messages in CSV: {len(total_ids)}")
    else:
        click.echo("Search complete.")
        click.echo(f"  Metadata saved to: {output_csv}")
    click.echo()
    click.echo("Next step: gmex prep " + output_csv + " <output.json>")


def load_json_data(json_path):
    """Load data from JSON file, returning empty list if doesn't exist."""
    if not Path(json_path).exists():
        return []
    with open(json_path, "r") as f:
        return json.load(f)


def parse_csv_to_items(csv_path):
    """Parse CSV file into list of item dicts."""
    header_map = {
        "Date": "date",
        "Message ID": "id",
        "Thread ID": "threadId",
        "From": "from",
        "To": "to",
        "Subject": "subject"
    }

    items = []
    with open(csv_path, "r", newline="") as f:
        reader = csv.reader(f)
        header = [h.strip() for h in next(reader)]

        for row in reader:
            if not row:
                continue
            item = {"body": "pending"}
            for i, value in enumerate(row):
                if i < len(header):
                    csv_header = header[i]
                    json_key = header_map.get(csv_header, csv_header.replace(" ", ""))
                    item[json_key] = value.strip()
            items.append(item)

    return items


@cli.command()
@click.argument("input_csv", type=click.Path(), required=False)
@click.argument("output_json", type=click.Path(), required=False)
@click.option("--dry-run", is_flag=True, help="Show what would be done without making changes.")
@click.pass_context
def prep(ctx, input_csv, output_json, dry_run):
    """Convert CSV metadata to JSON with placeholder bodies.

    INPUT_CSV is the CSV file created by 'gmex search'.

    OUTPUT_JSON is the path to the output JSON file.

    Both arguments can be omitted if config.yaml provides file_prefix.

    This command is idempotent:
    - If JSON exists, new IDs from CSV are added (preserving existing body data)
    - Duplicate IDs are not created
    - Validates that all JSON IDs exist in CSV (exits with error if not)

    \b
    Examples:
      gmex prep emails.csv emails.json
      gmex prep                            # Use config.yaml defaults
      gmex prep --dry-run                  # Preview changes
    """
    config = ctx.obj.get("config", {})

    # Apply config defaults using prefix (config or default "emails")
    prefix = config.get("file_prefix", "emails")
    if input_csv is None:
        input_csv = f"{prefix}_metadata.csv"
    if output_json is None:
        output_json = f"{prefix}_emails.json"

    # Check that CSV exists
    if not Path(input_csv).exists():
        click.echo(f"Error: CSV file not found: {input_csv}", err=True)
        sys.exit(1)

    click.echo(f"Preparing '{output_json}' from '{input_csv}'...")

    # Parse CSV
    csv_items = parse_csv_to_items(input_csv)
    csv_ids = {item["id"] for item in csv_items}
    csv_by_id = {item["id"]: item for item in csv_items}

    click.echo(f"Found {len(csv_items)} messages in CSV.")

    # Load existing JSON if present
    json_path = Path(output_json)
    existing_data = load_json_data(output_json)
    existing_ids = {item["id"] for item in existing_data}
    existing_by_id = {item["id"]: item for item in existing_data}

    if existing_data:
        click.echo(f"Found {len(existing_data)} existing messages in JSON.")

        # Check for IDs in JSON that are NOT in CSV (integrity check)
        orphan_ids = existing_ids - csv_ids
        if orphan_ids:
            click.echo(f"Error: {len(orphan_ids)} message(s) in JSON are not in CSV:", err=True)
            for oid in list(orphan_ids)[:5]:
                click.echo(f"  - {oid}", err=True)
            if len(orphan_ids) > 5:
                click.echo(f"  ... and {len(orphan_ids) - 5} more", err=True)
            click.echo(err=True)
            click.echo("The CSV and JSON are out of sync.", err=True)
            click.echo("Either update the CSV with 'gmex search --add' or archive and start fresh.", err=True)
            sys.exit(1)

    # Find new IDs to add
    new_ids = csv_ids - existing_ids
    click.echo(f"New messages to add: {len(new_ids)}")

    if dry_run:
        click.echo()
        click.echo("Dry run - no changes made.")
        if new_ids:
            click.echo("Would add the following message IDs:")
            for nid in list(new_ids)[:10]:
                click.echo(f"  - {nid}")
            if len(new_ids) > 10:
                click.echo(f"  ... and {len(new_ids) - 10} more")
        return

    if not new_ids and existing_data:
        click.echo("No new messages to add. JSON is up to date.")
        return

    # Build final data: existing items + new items (preserving body data for existing)
    final_data = []

    # Keep existing items in their original order, updating metadata from CSV
    for item in existing_data:
        msg_id = item["id"]
        if msg_id in csv_by_id:
            # Update metadata from CSV but keep body
            updated = csv_by_id[msg_id].copy()
            updated["body"] = item.get("body", "pending")
            final_data.append(updated)

    # Add new items
    for msg_id in new_ids:
        final_data.append(csv_by_id[msg_id])

    # Write JSON
    with open(output_json, "w") as f:
        json.dump(final_data, f, indent=2)

    click.echo()
    if new_ids:
        click.echo(f"Added {len(new_ids)} new messages.")
    click.echo(f"Total messages in JSON: {len(final_data)}")
    click.echo()
    click.echo("Next step: gmex fill " + output_json)


@cli.command()
@click.argument("json_file", type=click.Path(), required=False)
@click.option("--limit", "-n", type=int, default=None, help="Limit number of messages to process.")
@click.option("--dry-run", is_flag=True, help="Show plan without processing.")
@click.pass_context
def fill(ctx, json_file, limit, dry_run):
    """Fetch and populate email bodies in the JSON file.

    JSON_FILE is the JSON file created by 'gmex prep'.
    Can be omitted if config.yaml provides file_prefix.

    \b
    Examples:
      gmex fill emails.json              # Process all pending messages
      gmex fill emails.json -n 3         # Process only 3 messages
      gmex fill --dry-run                # Show plan (using config.yaml)
    """
    config = ctx.obj.get("config", {})

    # Apply config defaults using prefix (config or default "emails")
    if json_file is None:
        prefix = config.get("file_prefix", "emails")
        json_file = f"{prefix}_emails.json"

    if not Path(json_file).exists():
        click.echo(f"Error: JSON file not found: {json_file}", err=True)
        sys.exit(1)

    if not check_gwsa():
        click.echo("Error: 'gwsa' command not found.", err=True)
        click.echo("Please install gworkspace-access: pipx install git+https://github.com/krisrowe/gworkspace-access.git", err=True)
        sys.exit(1)

    # Load JSON
    with open(json_file, "r") as f:
        data = json.load(f)

    total_count = len(data)
    processed_count = sum(1 for item in data if isinstance(item.get("body"), dict))

    # Find IDs to update (body is a string, not an object)
    ids_to_update = [item["id"] for item in data if isinstance(item.get("body"), str)]

    if limit is not None and limit >= 0:
        ids_to_process = ids_to_update[:limit]
    else:
        ids_to_process = ids_to_update

    click.echo("Execution Plan:")
    click.echo(f"  Total messages in JSON: {total_count}")
    click.echo(f"  Already processed: {processed_count}")
    click.echo(f"  To be processed in this run: {len(ids_to_process)}")

    if ids_to_process:
        click.echo("  IDs to be processed:")
        for msg_id in ids_to_process:
            click.echo(f"    - {msg_id}")
    else:
        click.echo("  All messages have already been processed.")

    click.echo()

    if dry_run:
        click.echo("Dry run enabled. Exiting without processing.")
        return

    if not ids_to_process:
        click.echo("No messages to process.")
        return

    # Create a lookup for quick access
    id_to_index = {item["id"]: i for i, item in enumerate(data)}

    processed_in_run = 0
    text_only_ids = []
    html_only_ids = []

    for i, msg_id in enumerate(ids_to_process, 1):
        click.echo(f"Processing message {i} of {len(ids_to_process)}: {msg_id}")

        # Fetch message
        result = subprocess.run(
            ["gwsa", "mail", "read", msg_id],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            click.echo(f"  Warning: Failed to fetch message {msg_id}. Skipping.", err=True)
            continue

        try:
            message_payload = json.loads(result.stdout)
        except json.JSONDecodeError:
            click.echo(f"  Warning: Failed to parse message {msg_id}. Skipping.", err=True)
            continue

        # Update the body in our data
        idx = id_to_index.get(msg_id)
        if idx is not None:
            # Validate that fetched message matches our metadata exactly
            existing = data[idx]

            # Helper to normalize empty values
            def normalize(val):
                if val is None or val == "N/A":
                    return ""
                return val

            # Validate all metadata fields - both must be empty or both must match
            validation_errors = []

            # Date (required field)
            fetched_date = normalize(message_payload.get("date"))
            existing_date = normalize(existing.get("date"))
            if fetched_date != existing_date:
                validation_errors.append(("date", existing_date, fetched_date))

            # Subject
            fetched_subject = normalize(message_payload.get("subject"))
            existing_subject = normalize(existing.get("subject"))
            if fetched_subject != existing_subject:
                validation_errors.append(("subject", existing_subject, fetched_subject))

            # From
            fetched_from = normalize(message_payload.get("from"))
            existing_from = normalize(existing.get("from"))
            if fetched_from != existing_from:
                validation_errors.append(("from", existing_from, fetched_from))

            # To
            fetched_to = normalize(message_payload.get("to"))
            existing_to = normalize(existing.get("to"))
            if fetched_to != existing_to:
                validation_errors.append(("to", existing_to, fetched_to))

            if validation_errors:
                click.echo(f"  ERROR: Metadata mismatch for message {msg_id}!", err=True)
                for field, expected, got in validation_errors:
                    click.echo(f"    {field}:", err=True)
                    click.echo(f"      JSON:    '{expected}'", err=True)
                    click.echo(f"      Fetched: '{got}'", err=True)
                click.echo("Aborting to prevent data corruption.", err=True)
                sys.exit(1)

            # Validation passed - update body only
            body = message_payload.get("body", {})
            data[idx]["body"] = body
            processed_in_run += 1

            # Track body type for summary
            has_text = bool((body.get("text") or "").strip()) if isinstance(body, dict) else False
            has_html = bool((body.get("html") or "").strip()) if isinstance(body, dict) else False

            if has_text and not has_html:
                text_only_ids.append(msg_id)
            elif has_html and not has_text:
                html_only_ids.append(msg_id)

            body_length = len(body.get("text", "") or "") if isinstance(body, dict) else 0
            click.echo(f"  Updated: {fetched_date} | {body_length} chars")

    # Save updated JSON
    with open(json_file, "w") as f:
        json.dump(data, f, indent=2)

    click.echo()

    # Report body type issues
    if html_only_ids:
        click.echo(f"HTML-only bodies ({len(html_only_ids)} messages - will be converted to text for TXT export):")
        for mid in html_only_ids:
            click.echo(f"  - {mid}")
        click.echo()

    if text_only_ids:
        click.echo(f"Text-only bodies ({len(text_only_ids)} messages - no HTML version available):")
        for mid in text_only_ids:
            click.echo(f"  - {mid}")
        click.echo()

    click.echo("Run Summary:")
    click.echo(f"  Messages updated in this run: {processed_in_run}")

    remaining = sum(1 for item in data if isinstance(item.get("body"), str))
    if remaining > 0:
        click.echo(f"  Messages still pending: {remaining}")
        click.echo()
        click.echo(f"Next step: gmex fill {json_file}")
    else:
        click.echo("  All message bodies have been populated.")
        click.echo()
        click.echo(f"Next step: gmex readable {json_file}")


@cli.command()
@click.argument("json_file", type=click.Path(), required=False)
@click.option("--output", "-o", default=None, help="Base name for output files (without extension).")
@click.pass_context
def readable(ctx, json_file, output):
    """Export emails to human-readable HTML and TXT files.

    JSON_FILE is the JSON file with populated bodies (from 'gmex fill').
    Can be omitted if config.yaml provides file_prefix.

    Creates two files: <basename>-export.html and <basename>-export.txt

    \b
    Examples:
      gmex readable emails.json                    # Creates emails-export.html and emails-export.txt
      gmex readable -o my_export                   # Use config.yaml, custom output name
    """
    config = ctx.obj.get("config", {})

    # Apply config defaults using prefix (config or default "emails")
    prefix = config.get("file_prefix", "emails")
    if json_file is None:
        json_file = f"{prefix}_emails.json"

    if not Path(json_file).exists():
        click.echo(f"Error: JSON file not found: {json_file}", err=True)
        sys.exit(1)

    # Load JSON
    with open(json_file, "r") as f:
        data = json.load(f)

    # Check that all emails have bodies
    pending_count = sum(1 for item in data if isinstance(item.get("body"), str))

    if pending_count > 0:
        click.echo(f"Error: {pending_count} message(s) still have pending bodies.", err=True)
        click.echo()
        click.echo("You must populate all email bodies before exporting.", err=True)
        click.echo(f"Run: gmex fill {json_file}", err=True)
        sys.exit(1)

    # Determine output prefix
    if output:
        out_prefix = output
    else:
        out_prefix = get_prefix_from_path(json_file)

    html_file = f"{out_prefix}_export.html"
    txt_file = f"{out_prefix}_export.txt"

    click.echo(f"Exporting {len(data)} emails to readable formats...")

    # Sort by date (newest first)
    def parse_date(item):
        from email.utils import parsedate_to_datetime
        try:
            return parsedate_to_datetime(item.get("date", ""))
        except:
            return None

    sorted_data = sorted(data, key=lambda x: parse_date(x) or "", reverse=True)

    # Generate HTML
    html_content, text_only_ids = generate_html(sorted_data)
    with open(html_file, "w") as f:
        f.write(html_content)
    click.echo(f"  Created: {html_file}")

    # Generate TXT
    txt_content, html_only_ids = generate_txt(sorted_data)
    with open(txt_file, "w") as f:
        f.write(txt_content)
    click.echo(f"  Created: {txt_file}")

    click.echo()

    # Report conversions with ID lists
    if text_only_ids:
        click.echo(f"Text-only bodies ({len(text_only_ids)} messages - escaped text used in HTML export):")
        for msg_id in text_only_ids:
            click.echo(f"  - {msg_id}")
        click.echo()

    if html_only_ids:
        click.echo(f"HTML-only bodies ({len(html_only_ids)} messages - converted to text for TXT export):")
        for msg_id in html_only_ids:
            click.echo(f"  - {msg_id}")
        click.echo()

    click.echo("Export complete.")


def strip_html_tags(html_content):
    """Extract plain text from HTML by stripping tags."""
    import re
    # Remove script and style elements
    text = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
    # Replace br and p tags with newlines
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</p>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</div>', '\n', text, flags=re.IGNORECASE)
    # Remove all remaining tags
    text = re.sub(r'<[^>]+>', '', text)
    # Decode HTML entities
    import html as html_module
    text = html_module.unescape(text)
    # Clean up whitespace
    text = re.sub(r'\n\s*\n', '\n\n', text)
    return text.strip()


def generate_html(data):
    """Generate HTML export of emails.

    Uses the original HTML body from Gmail when available. Falls back to
    text body (escaped and wrapped in pre-wrap styling) if no HTML body exists.

    Returns tuple of (html_content, text_only_ids) where text_only_ids is a list
    of message IDs that had only text body (no HTML version, so text was escaped).
    """
    import html

    lines = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        "<meta charset=\"UTF-8\">",
        "<title>Email Export</title>",
        "<style>",
        "body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; background: #f5f5f5; }",
        ".email { background: white; border-radius: 8px; padding: 20px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }",
        ".email-header { border-bottom: 1px solid #eee; padding-bottom: 10px; margin-bottom: 15px; }",
        ".email-meta { color: #666; font-size: 14px; margin: 4px 0; }",
        ".email-subject { font-size: 18px; font-weight: 600; margin: 0 0 10px 0; }",
        ".email-body { line-height: 1.6; }",
        ".email-body-text { white-space: pre-wrap; font-family: inherit; }",
        ".email-index { color: #999; font-size: 12px; float: right; }",
        "</style>",
        "</head>",
        "<body>",
        f"<h1>Email Export ({len(data)} messages)</h1>",
    ]

    text_only_ids = []

    for i, item in enumerate(data, 1):
        subject = html.escape(item.get("subject", "") or "(No Subject)")
        from_addr = html.escape(item.get("from", ""))
        to_addr = html.escape(item.get("to", ""))
        date = html.escape(item.get("date", ""))
        msg_id = item.get("id", "")

        body_obj = item.get("body", {})
        if isinstance(body_obj, dict):
            body_text = body_obj.get("text", "") or ""
            body_html = body_obj.get("html", "") or ""
        else:
            body_text = str(body_obj)
            body_html = ""

        # Prefer HTML body, fall back to escaped text
        if body_html.strip():
            # Use original HTML body directly
            body_content = f"<div class=\"email-body\">{body_html}</div>"
        elif body_text.strip():
            # Fall back to escaped text with pre-wrap
            body_content = f"<div class=\"email-body email-body-text\">{html.escape(body_text)}</div>"
            if msg_id:
                text_only_ids.append(msg_id)
        else:
            body_content = "<div class=\"email-body\">(No body)</div>"

        lines.extend([
            "<div class=\"email\">",
            "<div class=\"email-header\">",
            f"<span class=\"email-index\">#{i}</span>",
            f"<h2 class=\"email-subject\">{subject}</h2>",
            f"<p class=\"email-meta\"><strong>From:</strong> {from_addr}</p>",
            f"<p class=\"email-meta\"><strong>To:</strong> {to_addr}</p>",
            f"<p class=\"email-meta\"><strong>Date:</strong> {date}</p>",
            "</div>",
            body_content,
            "</div>",
        ])

    lines.extend([
        "</body>",
        "</html>",
    ])

    return "\n".join(lines), text_only_ids


def generate_txt(data):
    """Generate plain text export of emails.

    Returns tuple of (content, degraded_ids) where degraded_ids is a list of
    message IDs that had to be converted from HTML to text.
    """
    lines = [
        f"EMAIL EXPORT ({len(data)} messages)",
        "=" * 80,
        "",
    ]

    degraded_ids = []

    for i, item in enumerate(data, 1):
        subject = item.get("subject", "") or "(No Subject)"
        from_addr = item.get("from", "")
        to_addr = item.get("to", "")
        date = item.get("date", "")
        msg_id = item.get("id", "")

        body_obj = item.get("body", {})
        if isinstance(body_obj, dict):
            body_text = body_obj.get("text", "") or ""
            body_html = body_obj.get("html", "") or ""
        else:
            body_text = str(body_obj)
            body_html = ""

        # If no text body, try to extract from HTML
        if not body_text.strip() and body_html.strip():
            body_text = strip_html_tags(body_html)
            if msg_id:
                degraded_ids.append(msg_id)

        lines.extend([
            f"[{i}] {subject}",
            "-" * 80,
            f"From: {from_addr}",
            f"To: {to_addr}",
            f"Date: {date}",
            "",
            body_text,
            "",
            "=" * 80,
            "",
        ])

    # Add degraded emails summary at the end if any
    if degraded_ids:
        lines.extend([
            "",
            f"NOTE: {len(degraded_ids)} email(s) were converted from HTML to plain text:",
            "-" * 80,
        ])
        for msg_id in degraded_ids:
            lines.append(f"  - {msg_id}")
        lines.append("")

    return "\n".join(lines), degraded_ids


@cli.command()
@click.argument("json_file", type=click.Path(), required=False)
@click.pass_context
def check(ctx, json_file):
    """Check the status of a JSON file.

    Shows counts of total emails, populated bodies, and pending bodies.
    JSON_FILE can be omitted if config.yaml provides base_name.

    \b
    Example:
      gmex check emails.json
      gmex check                 # Use config.yaml
    """
    config = ctx.obj.get("config", {})

    # Apply config defaults using prefix (config or default "emails")
    if json_file is None:
        prefix = config.get("file_prefix", "emails")
        json_file = f"{prefix}_emails.json"

    if not Path(json_file).exists():
        click.echo(f"Error: JSON file not found: {json_file}", err=True)
        sys.exit(1)

    with open(json_file, "r") as f:
        data = json.load(f)

    total = len(data)
    populated = sum(1 for item in data if isinstance(item.get("body"), dict))
    pending = sum(1 for item in data if isinstance(item.get("body"), str))
    with_subject = sum(1 for item in data if item.get("subject"))

    # Get date range
    from email.utils import parsedate_to_datetime
    dates = []
    for item in data:
        try:
            dt = parsedate_to_datetime(item.get("date", ""))
            dates.append((dt, item.get("date")))
        except:
            pass

    click.echo(f"JSON file: {json_file}")
    click.echo()
    click.echo(f"  Total emails: {total}")
    click.echo(f"  Bodies populated: {populated}")
    click.echo(f"  Bodies pending: {pending}")
    click.echo(f"  With subject: {with_subject}")

    if dates:
        dates.sort()
        click.echo(f"  Earliest: {dates[0][1]}")
        click.echo(f"  Latest: {dates[-1][1]}")


@cli.command()
@click.argument("txt_file", type=click.Path(), required=False)
@click.option("--output", "-o", default=None, help="Output JSON file name.")
@click.pass_context
def parse(ctx, txt_file, output):
    """Parse a TXT export back to JSON format for comparison.

    Reads the plain text export format created by 'gmex readable' and
    recreates a JSON structure that can be compared with the original.

    The output JSON will have emails sorted by date (newest first), matching
    the order in the readable export.

    \b
    Examples:
      gmex parse                           # Uses {prefix}_export.txt -> {prefix}_parsed.json
      gmex parse myproject_export.txt      # Parse specific file
      gmex parse -o compare.json           # Custom output name
    """
    config = ctx.obj.get("config", {})
    prefix = config.get("file_prefix", "emails")

    # Determine input file
    if txt_file is None:
        txt_file = f"{prefix}_export.txt"

    if not Path(txt_file).exists():
        click.echo(f"Error: TXT file not found: {txt_file}", err=True)
        sys.exit(1)

    # Determine output file
    if output is None:
        out_prefix = get_prefix_from_path(txt_file)
        output = f"{out_prefix}_parsed.json"

    click.echo(f"Parsing '{txt_file}'...")

    with open(txt_file, "r") as f:
        content = f.read()

    emails = parse_txt_export(content)

    # Write JSON output
    with open(output, "w") as f:
        json.dump(emails, f, indent=2)

    click.echo(f"  Created: {output}")
    click.echo()

    # TXT stats
    calculate_export_stats(emails, "TXT Export")

    # Check for HTML export and merge body.html into parsed data
    html_file = txt_file.replace("_export.txt", "_export.html")
    if Path(html_file).exists():
        click.echo()
        with open(html_file, "r") as f:
            html_content = f.read()
        html_emails = parse_html_export(html_content)
        calculate_export_stats(html_emails, "HTML Export")

        # Merge HTML bodies into TXT-parsed emails (match by index since both are same order)
        if len(emails) == len(html_emails):
            for i, html_email in enumerate(html_emails):
                html_body = html_email.get("body", {}).get("html")
                if html_body:
                    emails[i]["body"]["html"] = html_body
                else:
                    emails[i]["body"]["html"] = None

            # Re-write the merged JSON
            with open(output, "w") as f:
                json.dump(emails, f, indent=2)
            click.echo()
            click.echo(f"  Merged HTML bodies into: {output}")
        else:
            click.echo()
            click.echo(f"  Warning: Email count mismatch (TXT: {len(emails)}, HTML: {len(html_emails)}). HTML bodies not merged.")
    else:
        click.echo()
        click.echo("HTML Export Stats:")
        click.echo(f"  File not found: {html_file}")

    click.echo()
    click.echo("To verify the export was faithful:")
    click.echo(f"  gmex verify")


def parse_txt_export(content):
    """Parse the TXT export format back to a list of email dicts."""
    emails = []
    lines = content.split("\n")

    i = 0
    # Skip header
    while i < len(lines):
        line = lines[i]
        if line.startswith("=" * 10):
            i += 1
            break
        i += 1

    # Parse each email block
    while i < len(lines):
        # Skip empty lines
        while i < len(lines) and lines[i].strip() == "":
            i += 1

        if i >= len(lines):
            break

        # Look for [N] Subject line
        line = lines[i]
        if not line.startswith("["):
            i += 1
            continue

        # Parse subject from [N] Subject format
        bracket_end = line.find("]")
        if bracket_end == -1:
            i += 1
            continue

        subject = line[bracket_end + 1:].strip()
        if subject == "(No Subject)":
            subject = ""
        i += 1

        # Skip separator line (---...)
        if i < len(lines) and lines[i].startswith("-" * 10):
            i += 1

        # Parse headers
        from_addr = ""
        to_addr = ""
        date = ""

        while i < len(lines):
            line = lines[i]
            if line.startswith("From: "):
                from_addr = line[6:]
                i += 1
            elif line.startswith("To: "):
                to_addr = line[4:]
                i += 1
            elif line.startswith("Date: "):
                date = line[6:]
                i += 1
            elif line == "":
                i += 1
                break
            else:
                i += 1
                break

        # Collect body until we hit the separator (===...)
        body_lines = []
        while i < len(lines):
            line = lines[i]
            if line.startswith("=" * 10):
                i += 1
                break
            body_lines.append(line)
            i += 1

        # Remove trailing empty lines from body
        while body_lines and body_lines[-1] == "":
            body_lines.pop()

        body_text = "\n".join(body_lines)

        emails.append({
            "subject": subject,
            "from": from_addr,
            "to": to_addr,
            "date": date,
            "body": {
                "text": body_text
            }
        })

    return emails


def parse_html_export(content):
    """Parse the HTML export format back to a list of email dicts.

    Distinguishes between emails that had HTML body (class="email-body") and
    text-only emails (class="email-body email-body-text"). For HTML bodies,
    stores the raw HTML. For text-only, unescapes to get original text.
    """
    import re
    import html as html_module

    emails = []

    # Find all email divs - match header info and body class, then extract body separately
    email_pattern = re.compile(
        r'<div class="email">.*?<h2 class="email-subject">(.*?)</h2>.*?'
        r'<strong>From:</strong>\s*(.*?)</p>.*?'
        r'<strong>To:</strong>\s*(.*?)</p>.*?'
        r'<strong>Date:</strong>\s*(.*?)</p>.*?'
        r'<div class="(email-body[^"]*)">(.*?)</div>\n</div>',
        re.DOTALL
    )

    for match in email_pattern.finditer(content):
        subject = html_module.unescape(match.group(1).strip())
        from_addr = html_module.unescape(match.group(2).strip())
        to_addr = html_module.unescape(match.group(3).strip())
        date = html_module.unescape(match.group(4).strip())
        body_class = match.group(5)
        body_content = match.group(6).strip()

        if subject == "(No Subject)":
            subject = ""

        # Check if this was a text-only email (has email-body-text class)
        is_text_only = "email-body-text" in body_class

        if is_text_only:
            # Text-only: unescape to get original text
            emails.append({
                "subject": subject,
                "from": from_addr,
                "to": to_addr,
                "date": date,
                "body": {
                    "text": html_module.unescape(body_content),
                    "html": None
                }
            })
        else:
            # HTML body: keep as-is (it's the original HTML from Gmail)
            emails.append({
                "subject": subject,
                "from": from_addr,
                "to": to_addr,
                "date": date,
                "body": {
                    "text": None,
                    "html": body_content
                }
            })

    return emails


def calculate_export_stats(emails, label):
    """Calculate and display stats for a list of parsed emails."""
    from email.utils import parsedate_to_datetime

    if not emails:
        click.echo(f"{label} Stats:")
        click.echo("  No emails found.")
        return

    # Body length stats
    body_lengths = []
    for email in emails:
        body = email.get("body", {})
        if isinstance(body, dict):
            text = body.get("text", "") or ""
        else:
            text = str(body)
        body_lengths.append(len(text))

    # Date stats
    parsed_dates = []
    for email in emails:
        try:
            dt = parsedate_to_datetime(email.get("date", ""))
            parsed_dates.append((dt, email.get("date")))
        except:
            pass

    click.echo(f"{label} Stats:")
    click.echo(f"  Total emails: {len(emails)}")
    click.echo(f"  Emails with body: {sum(1 for l in body_lengths if l > 0)}")
    if body_lengths:
        click.echo(f"  Body length min: {min(body_lengths)} chars")
        click.echo(f"  Body length max: {max(body_lengths)} chars")
    if parsed_dates:
        parsed_dates.sort()
        click.echo(f"  Earliest: {parsed_dates[0][1]}")
        click.echo(f"  Latest: {parsed_dates[-1][1]}")


@cli.command()
@click.argument("json_file", type=click.Path(), required=False)
@click.argument("parsed_file", type=click.Path(), required=False)
@click.pass_context
def verify(ctx, json_file, parsed_file):
    """Verify that the TXT export faithfully captured the original emails.

    Compares the original JSON file with the parsed JSON (from 'gmex parse'),
    accounting for expected differences like sort order and missing fields.

    \b
    Examples:
      gmex verify                              # Uses {prefix}_emails.json and {prefix}_parsed.json
      gmex verify original.json parsed.json   # Compare specific files
    """
    config = ctx.obj.get("config", {})
    prefix = config.get("file_prefix", "emails")

    # Determine files
    if json_file is None:
        json_file = f"{prefix}_emails.json"
    if parsed_file is None:
        parsed_file = f"{prefix}_parsed.json"

    if not Path(json_file).exists():
        click.echo(f"Error: Original JSON not found: {json_file}", err=True)
        click.echo("Run 'gmex fill' first.", err=True)
        sys.exit(1)

    if not Path(parsed_file).exists():
        click.echo(f"Error: Parsed JSON not found: {parsed_file}", err=True)
        click.echo("Run 'gmex parse' first.", err=True)
        sys.exit(1)

    click.echo(f"Comparing '{json_file}' with '{parsed_file}'...")

    # Load both files
    with open(json_file, "r") as f:
        original = json.load(f)
    with open(parsed_file, "r") as f:
        parsed = json.load(f)

    # Sort original by date (newest first) to match readable export order
    from email.utils import parsedate_to_datetime

    def parse_date(item):
        try:
            return parsedate_to_datetime(item.get("date", ""))
        except:
            return None

    original_sorted = sorted(original, key=lambda x: parse_date(x) or "", reverse=True)

    # Compare
    if len(original_sorted) != len(parsed):
        click.echo(f"  MISMATCH: Count differs - original: {len(original_sorted)}, parsed: {len(parsed)}", err=True)
        sys.exit(1)

    differences = []
    for i, (orig, pars) in enumerate(zip(original_sorted, parsed), 1):
        email_diffs = []

        # Compare subject
        orig_subj = orig.get("subject", "") or ""
        pars_subj = pars.get("subject", "") or ""
        if orig_subj != pars_subj:
            email_diffs.append(f"subject: '{orig_subj}' vs '{pars_subj}'")

        # Compare from
        if orig.get("from", "") != pars.get("from", ""):
            email_diffs.append(f"from: '{orig.get('from', '')}' vs '{pars.get('from', '')}'")

        # Compare to
        if orig.get("to", "") != pars.get("to", ""):
            email_diffs.append(f"to: '{orig.get('to', '')}' vs '{pars.get('to', '')}'")

        # Compare date
        if orig.get("date", "") != pars.get("date", ""):
            email_diffs.append(f"date: '{orig.get('date', '')}' vs '{pars.get('date', '')}'")

        # Compare body text and html (normalize line endings)
        orig_body = orig.get("body", {})
        if isinstance(orig_body, dict):
            orig_text = orig_body.get("text", "") or ""
            orig_html = orig_body.get("html", "") or ""
        else:
            orig_text = str(orig_body)
            orig_html = ""
        orig_text = orig_text.replace("\r\n", "\n").strip()
        orig_html = orig_html.replace("\r\n", "\n").strip()

        pars_body = pars.get("body", {})
        if isinstance(pars_body, dict):
            pars_text = pars_body.get("text", "") or ""
            pars_html = pars_body.get("html", "") or ""
        else:
            pars_text = str(pars_body)
            pars_html = ""
        pars_text = pars_text.strip()
        pars_html = pars_html.strip()

        if orig_text != pars_text:
            # Find first difference location
            min_len = min(len(orig_text), len(pars_text))
            diff_pos = next((j for j in range(min_len) if orig_text[j] != pars_text[j]), min_len)
            email_diffs.append(f"body.text differs at char {diff_pos} (orig: {len(orig_text)}, parsed: {len(pars_text)})")

        # Compare body HTML
        if orig_html != pars_html:
            min_len = min(len(orig_html), len(pars_html))
            diff_pos = next((j for j in range(min_len) if orig_html[j] != pars_html[j]), min_len)
            email_diffs.append(f"body.html differs at char {diff_pos} (orig: {len(orig_html)}, parsed: {len(pars_html)})")

        if email_diffs:
            differences.append((i, orig.get("subject", "(No Subject)"), email_diffs))

    if differences:
        click.echo()
        click.echo(f"  Found {len(differences)} email(s) with differences:")
        for idx, subj, diffs in differences[:10]:  # Show first 10
            click.echo(f"    [{idx}] {subj}")
            for d in diffs:
                click.echo(f"        - {d}")
        if len(differences) > 10:
            click.echo(f"    ... and {len(differences) - 10} more")
        click.echo()
        click.echo("VERIFICATION FAILED", err=True)
        sys.exit(1)
    else:
        click.echo()
        click.echo(f"  Compared {len(original_sorted)} emails.")
        click.echo("  All fields match (subject, from, to, date, body.text, body.html).")
        click.echo()
        click.echo("VERIFICATION PASSED")


def main():
    cli()


if __name__ == "__main__":
    main()
