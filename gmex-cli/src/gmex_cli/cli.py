"""Gmail Extractor CLI - Main entry point."""

import click
import sys
import os
import json
import logging
from datetime import datetime
from email_archive import EmailStore
from gmex_sdk.extractor import GmailExtractor
from gmex_sdk.config import get_token_status, import_token

# Configure Logging (Default to INFO)
log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, log_level), 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@click.group()
@click.version_option()
@click.pass_context
def cli(ctx):
    """Gmail Extractor (gmex) - Sync Gmail messages to local archive.

    Environment Variables:
      - GMEX_QUERY: Default Gmail search query
      - GMEX_LIMIT: Default max emails to fetch
      - EMAIL_ARCHIVE_DATA_DIR: Data storage path
    """
    ctx.ensure_object(dict)
    ctx.obj["store"] = EmailStore()
    ctx.obj["extractor"] = GmailExtractor()

@cli.group()
def token():
    """Manage authentication tokens."""
    pass

@token.command("show")
def token_show():
    """Show the expected token file location and status."""
    status = get_token_status()
    click.echo(f"Expected Path: {status['path']}", err=True)
    if status['exists']:
        click.echo(f"Status: FOUND ({status['size']} bytes)", err=True)
    else:
        click.echo("Status: MISSING", err=True)

@token.command("import")
def token_import():
    """Import a token JSON from stdin."""
    # Read from stdin
    try:
        data = sys.stdin.read().strip()
        if not data:
            click.secho("Error: No data received on stdin.", fg="red", err=True)
            sys.exit(1)
            
        # Validate JSON
        json_data = json.loads(data)
        
        # Save via SDK
        import_token(json_data)
            
        click.secho(f"Success: Token imported.", fg="green", err=True)
    except json.JSONDecodeError:
        click.secho("Error: Invalid JSON received.", fg="red", err=True)
        sys.exit(1)
    except Exception as e:
        click.secho(f"Error: {e}", fg="red", err=True)
        sys.exit(1)

@cli.command()
@click.argument("query", required=False)
@click.option("--limit", "-n", default=None, type=int, help="Max emails to fetch.")
@click.pass_context
def sync(ctx, query, limit):
    """Sync emails from Gmail to local store."""
    store = ctx.obj["store"]
    extractor = ctx.obj["extractor"]
    
    if not extractor.check_auth():
        click.secho("Error: Not authenticated.", fg="red", err=True)
        click.echo("Run 'gmex token show' to see where to put your token.", err=True)
        click.echo("Or use 'gwsa token generate ... | gmex token import' to set it up.", err=True)
        sys.exit(1)

    click.echo(f"Initializing sync...", err=True)
    click.echo(f"Storage: {store.root}", err=True)

    try:
        messages = extractor.search(query, limit)
    except Exception as e:
        click.secho(f"Search failed: {e}", fg="red", err=True)
        sys.exit(1)

    new_messages = []
    for msg in messages:
        if not store.exists(msg.get("id")):
            new_messages.append(msg)
            
    click.echo(f"Found {len(messages)} messages. New: {len(new_messages)}", err=True)
    
    if not new_messages:
        return

    with click.progressbar(new_messages, label="Syncing") as bar:
        for msg in bar:
            msg_id = msg.get("id")
            try:
                full_email = extractor.get_message(msg_id)
                
                # Parse date
                date_str = full_email.get("date")
                try:
                    from email.utils import parsedate_to_datetime
                    dt = parsedate_to_datetime(date_str)
                except:
                    dt = datetime.now()
                
                # Prepare Headers for .meta (Canonical field names)
                headers = {
                    "Subject": full_email.get("subject", ""),
                    "From": full_email.get("from", ""),
                    "To": full_email.get("to", ""),
                    "Thread-ID": full_email.get("threadId", ""),
                    "Labels": full_email.get("labelIds", [])
                }
                
                # Content
                content = {
                    "snippet": full_email.get("snippet"),
                    "body_text": full_email.get("body", {}).get("text"),
                    "body_html": full_email.get("body", {}).get("html"),
                    "attachments": full_email.get("attachments", []) 
                }
                
                store.save(msg_id, dt, headers, content)
            except Exception as e:
                logger.error(f"Failed to sync {msg_id}: {e}")

    click.echo("Sync complete.", err=True)

def main():
    cli()

if __name__ == "__main__":
    main()
