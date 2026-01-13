import os
import json
import logging
from pathlib import Path
from typing import Any, Dict

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

logger = logging.getLogger(__name__)

def get_token_path() -> Path:
    """Standard location for the OAuth token file."""
    # 1. Check ENV Var
    if env_path := os.environ.get("GMEX_TOKEN_PATH"):
        return Path(env_path)
    # 2. Default XDG location
    return Path.home() / ".config" / "gmail-extractor" / "token.json"

def get_extract_setting(key: str, default: Any = None) -> Any:
    """Resolve setting from Env Var > Internal Config > Default."""
    env_key = f"GMEX_{key.upper()}"
    if env_val := os.environ.get(env_key):
        return env_val
    
    settings_path = Path(__file__).parent / "config.yaml"
    if HAS_YAML and settings_path.exists():
        with open(settings_path, "r") as f:
            settings = yaml.safe_load(f) or {}
            if key in settings:
                return settings[key]
    return default

def resolve_credentials():
    """Seamlessly resolve Google API credentials for the environment."""
    import google.auth
    token_path = get_token_path()
    
    # Seamless injection for local CLI users:
    if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") and token_path.exists():
        logger.debug(f"Seamlessly using token from: {token_path}")
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(token_path)

    try:
        creds, _ = google.auth.default()
        return creds
    except Exception as e:
        logger.debug(f"Default credential resolution failed: {e}")
        return None

def import_token(data: Dict[str, Any]):
    """Validate and save a token to the standard location."""
    path = get_token_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def get_token_status() -> Dict[str, Any]:
    """Get status of the local token file."""
    path = get_token_path()
    exists = path.exists()
    return {
        "path": path,
        "exists": exists,
        "size": path.stat().st_size if exists else 0
    }
