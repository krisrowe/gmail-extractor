import json
import os
import logging
from pathlib import Path
from email.parser import HeaderParser
from datetime import datetime
from typing import Dict, List, Optional, Any, Union

logger = logging.getLogger(__name__)

def _resolve_data_dir() -> Path:
    """Resolve the data directory from environment configuration."""
    if env_path := os.environ.get("EMAIL_ARCHIVE_DATA_DIR"):
        return Path(env_path)
    xdg_data = os.environ.get("XDG_DATA_HOME")
    if xdg_data:
        return Path(xdg_data) / "email-archive"
    return Path.home() / ".local" / "share" / "email-archive"

class EmailStore:
    """
    High-performance email storage SDK.
    Encapsulates a dual-file storage strategy (RFC 5322 Headers + JSON Body).
    """
    def __init__(self, root_dir: Union[str, Path, None] = None):
        if root_dir is None:
            self.root = _resolve_data_dir()
        else:
            self.root = Path(root_dir)
        
        self.root.mkdir(parents=True, exist_ok=True)

    def _get_paths(self, message_id: str, date: Optional[datetime] = None) -> tuple[Path, Path]:
        if date is None:
            matches = list(self.root.glob(f"*_{message_id}.meta"))
            if matches:
                meta_path = matches[0]
                body_path = meta_path.with_suffix(".body")
                return meta_path, body_path
            raise ValueError(f"Email {message_id} not found.")

        prefix = date.strftime("%Y%m%d-%H%M%S")
        filename = f"{prefix}_{message_id}"
        return self.root / f"{filename}.meta", self.root / f"{filename}.body"

    def save(self, message_id: str, date: datetime, headers: Dict[str, Any], content: Dict[str, Any]):
        """Atomic save of an email."""
        meta_path, body_path = self._get_paths(message_id, date)

        # 1. Save Content (JSON)
        temp_body = body_path.with_suffix(".body.tmp")
        with open(temp_body, "w", encoding="utf-8") as f:
            json.dump(content, f, indent=2, ensure_ascii=False)
        os.rename(temp_body, body_path)

        # 2. Save Headers (RFC 5322)
        temp_meta = meta_path.with_suffix(".meta.tmp")
        with open(temp_meta, "w", encoding="utf-8") as f:
            f.write(f"ID: {message_id}\n")
            f.write(f"Date: {date.isoformat()}\n")
            for key, val in headers.items():
                if key in ["ID", "Date"]:
                    continue
                if isinstance(val, list):
                    for v in val:
                        f.write(f"{key}: {v}\n")
                else:
                    # Fix: Sanitize newlines to avoid corruption/syntax errors
                    clean_val = str(val).replace('\n', ' ')
                    f.write(f"{key}: {clean_val}\n")
        os.rename(temp_meta, meta_path)

    def attach(self, message_id: str, key: str, data: Any):
        """Save a sidecar file linked to the email (e.g. analysis.json)."""
        meta_path, _ = self._get_paths(message_id)
        # 2026..._msg123.meta -> 2026..._msg123.analysis.json
        attach_path = meta_path.parent / f"{meta_path.stem}.{key}"
        with open(attach_path, "w", encoding="utf-8") as f:
            if isinstance(data, (dict, list)):
                json.dump(data, f, indent=2, ensure_ascii=False)
            else:
                f.write(str(data))

    def exists(self, message_id: str) -> bool:
        return any(self.root.glob(f"*_{message_id}.meta"))

    def get(self, message_id: str, include_content: bool = False) -> Optional[Dict[str, Any]]:
        """Retrieve an email by ID."""
        matches = list(self.root.glob(f"*_{message_id}.meta"))
        if not matches:
            return None
        
        meta_path = matches[0]
        data = {}
        
        # Load Headers
        with open(meta_path, "r", encoding="utf-8") as f:
            msg = HeaderParser().parse(f)
            for key in set(msg.keys()):
                vals = msg.get_all(key)
                data[key.lower()] = vals[0] if len(vals) == 1 else vals

        if include_content:
            body_path = meta_path.with_suffix(".body")
            if body_path.exists():
                with open(body_path, "r", encoding="utf-8") as f:
                    data.update(json.load(f))
        
        return data

    def list(self, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """List emails chronologically."""
        results = []
        for meta_path in sorted(self.root.glob("*.meta")):
            try:
                date_part, msg_id = meta_path.stem.split("_", 1)
                file_date = datetime.strptime(date_part, "%Y%m%d-%H%M%S")
                if since and file_date < since:
                    continue
                results.append({"id": msg_id, "date": file_date})
            except ValueError:
                continue
        return results
