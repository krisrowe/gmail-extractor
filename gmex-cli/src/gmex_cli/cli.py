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

log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, log_level), format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

@click.group()
@click.version_option()
@click.pass_context
def cli(ctx):
    """Gmail Extractor (gmex) - Fetch Gmail messages to local archive."""
    ctx.ensure_object(dict)
    ctx.obj["store"] = EmailStore()
    ctx.obj["extractor"] = GmailExtractor()

@cli.group()
def token():
    """Manage authentication tokens."""
    pass

@token.command("show")
def token_show():
    status = get_token_status()
    click.echo(f"Expected Path: {status[path]}", err=True)
    if status["exists"]: click.echo(f"Status: FOUND ({status['size']} bytes)", err=True)
    else: click.echo("Status: MISSING", err=True)

@token.command("import")
def token_import():
    try:
        data = sys.stdin.read().strip()
        if not data:
            click.secho("Error: No data received on stdin.", fg="red", err=True)
            sys.exit(1)
        import_token(json.loads(data))
        click.secho("Success: Token imported.", fg="green", err=True)
    except Exception as e:
        click.secho(f"Error: {e}", fg="red", err=True)
        sys.exit(1)

@cli.command()
@click.argument("query", required=False)
@click.option("--limit", "-n", default=None, type=int, help="Max emails to fetch.")
@click.pass_context
def fetch(ctx, query, limit):
    """Fetch emails from Gmail to local store."""
    store, extractor = ctx.obj["store"], ctx.obj["extractor"]
    if not extractor.check_auth():
        click.secho("Error: Not authenticated.", fg="red", err=True)
        sys.exit(1)

    logger.info("Fetcher: Cycle started.")
    try:
        messages = extractor.search(query, limit)
    except Exception as e:
        logger.error(f"Fetcher: Search failed: {e}")
        sys.exit(1)

    new_messages = [msg for msg in messages if not store.exists(msg.get("id"))]
    logger.info(f"Fetcher: Discovery complete. (Total: {len(messages)}, New: {len(new_messages)})")
    
    if not new_messages:
        logger.info("Fetcher: Cycle idle. (No new messages found)")
        return

    success_count = 0
    with click.progressbar(new_messages, label="Fetching") as bar:
        for msg in bar:
            try:
                msg_id = msg.get("id")
                full_email = extractor.get_message(msg_id)
                date_str = full_email.get("date")
                try:
                    from email.utils import parsedate_to_datetime
                    dt = parsedate_to_datetime(date_str)
                except: dt = datetime.now()
                
                headers = {
                    "Subject": full_email.get("subject", ""),
                    "From": full_email.get("from", ""),
                    "To": full_email.get("to", ""),
                    "Thread-ID": full_email.get("threadId", ""),
                    "Labels": full_email.get("labelIds", [])
                }
                content = {
                    "snippet": full_email.get("snippet"),
                    "body_text": full_email.get("body", {}).get("text"),
                    "body_html": full_email.get("body", {}).get("html"),
                    "attachments": full_email.get("attachments", []) 
                }
                store.save(msg_id, dt, headers, content)
                logger.info(f"Fetcher: Stored email {msg_id}")
                success_count += 1
            except Exception as e: 
                logger.error(f"Fetcher: Failed to fetch {msg_id}: {e}")

    logger.info(f"Fetcher: Cycle completed. (Processed: {success_count}/{len(new_messages)})")

def main(): cli()
if __name__ == "__main__": main()
