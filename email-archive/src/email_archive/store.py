import json
import os
import logging
from pathlib import Path
from email.parser import HeaderParser
from datetime import datetime
from typing import Dict, List, Optional, Any, Union

logger = logging.getLogger(__name__)

class EmailStore:
    def exists(self, message_id: str) -> bool:
        return any(self.root.glob(f"*_{message_id}.meta"))
    def __init__(self, root_dir: Union[str, Path, None] = None):
        if root_dir is None:
            if env_path := os.environ.get("EMAIL_ARCHIVE_DATA_DIR"):
                self.root = Path(env_path)
            else:
                xdg_data = os.environ.get("XDG_DATA_HOME")
                self.root = (Path(xdg_data) if xdg_data else Path.home() / ".local" / "share") / "email-archive"
        else:
            self.root = Path(root_dir)
        
        self.root.mkdir(parents=True, exist_ok=True)

    def _get_paths(self, message_id: str, date: Optional[datetime] = None) -> tuple[Path, Path]:
        if date is None:
            matches = list(self.root.glob(f"*_{message_id}.meta"))
            if matches:
                meta_path = matches[0]
                return meta_path, meta_path.with_suffix(".body")
            raise ValueError(f"Email {message_id} not found.")
        prefix = date.strftime("%Y%m%d-%H%M%S")
        filename = f"{prefix}_{message_id}"
        return self.root / f"{filename}.meta", self.root / f"{filename}.body"

    def save(self, message_id: str, date: datetime, headers: Dict[str, Any], content: Dict[str, Any]):
        meta_path, body_path = self._get_paths(message_id, date)
        temp_body = body_path.with_suffix(".body.tmp")
        with open(temp_body, "w", encoding="utf-8") as f:
            json.dump(content, f, indent=2, ensure_ascii=False)
        os.rename(temp_body, body_path)
        temp_meta = meta_path.with_suffix(".meta.tmp")
        with open(temp_meta, "w", encoding="utf-8") as f:
            f.write(f"ID: {message_id}\nDate: {date.isoformat()}\n")
            for key, val in headers.items():
                if key in ["ID", "Date"]: continue
                if isinstance(val, list):
                    for v in val: f.write(f"{key}: {v}\n")
                else:
                    f.write(key + ": " + str(val).replace("\n", " ") + "\n")
        os.rename(temp_meta, meta_path)

    def save_sidecar(self, message_id: str, key: str, data: Any):
        meta_path, _ = self._get_paths(message_id)
        sidecar_path = meta_path.parent / f"{meta_path.stem}.{key}"
        with open(sidecar_path, "w", encoding="utf-8") as f:
            if isinstance(data, (dict, list)): json.dump(data, f, indent=2, ensure_ascii=False)
            else: f.write(str(data))

    def has_sidecar(self, message_id: str, key: str) -> bool:
        """Existence check without full directory scan."""
        try:
            return any(self.root.glob(f"*_{message_id}.{key}"))
        except: return False

    def exists(self, message_id: str) -> bool:
        """Check if an email metadata file exists for the given ID."""
        return any(self.root.glob(f"*_{message_id}.meta"))

    def get_sidecar(self, message_id: str, key: str) -> Optional[Any]:
        try:
            meta_path, _ = self._get_paths(message_id)
            p = meta_path.parent / f"{meta_path.stem}.{key}"
            if not p.exists(): return None
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f) if (p.suffix == ".json" or key.endswith(".json")) else f.read()
        except: return None

    def list(self, since: Optional[datetime] = None, sidecar_missing: Optional[str] = None, limit: Optional[int] = None, newest_first: bool = False) -> List[Dict[str, Any]]:
        """
        List emails efficiently using os.scandir for high-volume directories.
        """
        since_str = since.strftime("%Y%m%d") if since else ""
        
        matches = []
        # scandir is a lazy iterator (no memory spike for 50k files)
        with os.scandir(self.root) as it:
            for entry in it:
                if not entry.is_file() or not entry.name.endswith(".meta"):
                    continue
                
                # Fast alphabetical filtering: "20260112..." > "20260101"
                if since_str and entry.name < since_str:
                    continue
                
                if sidecar_missing:
                    # Check for [STEM].[KEY] efficiently
                    stem = os.path.splitext(entry.name)[0]
                    if os.path.exists(os.path.join(self.root, f"{stem}.{sidecar_missing}")):
                        continue
                
                matches.append(entry.name)

        # Sort the filtered list (small list = fast sort)
        matches.sort(reverse=newest_first)
        
        if limit: matches = matches[:limit]

        results = []
        for name in matches:
            try:
                stem = os.path.splitext(name)[0]
                dt_part, msg_id = stem.split("_", 1)
                dt = datetime.strptime(dt_part, "%Y%m%d-%H%M%S")
                results.append({"id": msg_id, "date": dt})
            except: continue
            
        return results

    def get(self, message_id: str, include_content: bool = False) -> Optional[Dict[str, Any]]:
        matches = list(self.root.glob(f"*_{message_id}.meta"))
        if not matches: return None
        meta_path, data = matches[0], {}
        with open(meta_path, "r", encoding="utf-8") as f:
            msg = HeaderParser().parse(f)
            for k in set(msg.keys()):
                vals = msg.get_all(k)
                data[k.lower()] = vals[0] if len(vals) == 1 else vals
        if include_content:
            body_path = meta_path.with_suffix(".body")
            if body_path.exists():
                with open(body_path, "r", encoding="utf-8") as f: data.update(json.load(f))
        return data
