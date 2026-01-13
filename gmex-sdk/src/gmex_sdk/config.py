import json
import logging
from pathlib import Path
from typing import Any, Dict
from .paths import resolve_data_dir, resolve_token_path
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False
logger = logging.getLogger(__name__)
def get_token_path() -> Path: return resolve_token_path()
def get_extract_setting(key: str, default: Any = None) -> Any:
    import os
    env_key = f"GMEX_{key.upper()}"
    if env_val := os.environ.get(env_key): return env_val
    settings_path = Path(__file__).parent / "config.yaml"
    if HAS_YAML and settings_path.exists():
        with open(settings_path, "r") as f:
            settings = yaml.safe_load(f) or {}
            if key in settings: return settings[key]
    return default
def resolve_credentials():
    import os
    import google.auth
    token_path = resolve_token_path()
    if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") and token_path.exists():
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(token_path)
    try:
        creds, _ = google.auth.default()
        return creds
    except Exception: return None
def import_token(data: Dict[str, Any]):
    path = resolve_token_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f: json.dump(data, f, indent=2)
def get_token_status() -> Dict[str, Any]:
    path = resolve_token_path()
    exists = path.exists()
    return {"path": path, "exists": exists, "size": path.stat().st_size if exists else 0}
