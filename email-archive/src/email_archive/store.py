import json
import os
import logging
from pathlib import Path
from email.parser import HeaderParser
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

class EmailStore:
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
        self._id_index: Optional[Dict[str, str]] = None  # msg_id -> prefix

    def _get_id_index(self) -> Dict[str, str]:
        """Lazy-load index mapping msg_id -> filename prefix.

        Enables O(1) ID lookups instead of O(n) glob per lookup.
        """
        if self._id_index is not None:
            return self._id_index

        import time
        start = time.time()

        self._id_index = {}
        with os.scandir(self.root) as it:
            for entry in it:
                if entry.is_file() and entry.name.endswith(".meta"):
                    try:
                        stem = entry.name[:-5]  # strip .meta
                        prefix, msg_id = stem.split("_", 1)
                        self._id_index[msg_id] = prefix
                    except ValueError:
                        pass

        elapsed_ms = int((time.time() - start) * 1000)
        logger.debug(f"ID index loaded: {len(self._id_index)} emails in {elapsed_ms}ms")

        return self._id_index

    def _get_paths(self, message_id: str, date: Optional[datetime] = None) -> tuple[Path, Path]:
        if date is None:
            # O(1) lookup via index
            index = self._get_id_index()
            if message_id not in index:
                raise ValueError(f"Email {message_id} not found.")
            prefix = index[message_id]
            filename = f"{prefix}_{message_id}"
            return self.root / f"{filename}.meta", self.root / f"{filename}.body"
        # Normalize to UTC for consistent filename timestamps
        if date.tzinfo is not None:
            date = date.astimezone(ZoneInfo("UTC"))
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
        # Update index if loaded
        if self._id_index is not None:
            if date.tzinfo is not None:
                date = date.astimezone(ZoneInfo("UTC"))
            self._id_index[message_id] = date.strftime("%Y%m%d-%H%M%S")

    def save_sidecar(self, message_id: str, key: str, data: Any):
        meta_path, _ = self._get_paths(message_id)
        sidecar_path = meta_path.parent / f"{meta_path.stem}.{key}"
        with open(sidecar_path, "w", encoding="utf-8") as f:
            if isinstance(data, (dict, list)): json.dump(data, f, indent=2, ensure_ascii=False)
            else: f.write(str(data))

    def has_sidecar(self, message_id: str, key: str) -> bool:
        """Check if sidecar exists. O(1) via index."""
        index = self._get_id_index()
        if message_id not in index:
            return False
        prefix = index[message_id]
        sidecar_path = self.root / f"{prefix}_{message_id}.{key}"
        return sidecar_path.exists()

    def exists(self, message_id: str) -> bool:
        """Check if an email metadata file exists for the given ID."""
        return message_id in self._get_id_index()

    def get_sidecar(self, message_id: str, key: str) -> Optional[Any]:
        try:
            meta_path, _ = self._get_paths(message_id)
            p = meta_path.parent / f"{meta_path.stem}.{key}"
            if not p.exists(): return None
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f) if (p.suffix == ".json" or key.endswith(".json")) else f.read()
        except: return None

    def _date_range_to_utc(self, start_date: str, end_date: str, timezone: str) -> tuple[str, str]:
        """Convert local date range to UTC prefix range for comparison.

        Args:
            start_date: "YYYY-MM-DD" in user's timezone
            end_date: "YYYY-MM-DD" in user's timezone
            timezone: IANA timezone name

        Returns:
            (start_prefix, end_prefix) as UTC strings for comparison
        """
        from datetime import date, time, timedelta

        tz = ZoneInfo(timezone)
        start_d = date.fromisoformat(start_date)
        end_d = date.fromisoformat(end_date)

        # Start of start_date in local tz
        start_dt = datetime.combine(start_d, time.min, tzinfo=tz)
        # Start of day AFTER end_date (half-open interval)
        end_dt = datetime.combine(end_d + timedelta(days=1), time.min, tzinfo=tz)

        start_utc = start_dt.astimezone(ZoneInfo("UTC"))
        end_utc = end_dt.astimezone(ZoneInfo("UTC"))

        return start_utc.strftime("%Y%m%d-%H%M%S"), end_utc.strftime("%Y%m%d-%H%M%S")

    def list(self, start_date: str, end_date: str, timezone: str, sidecar_missing: Optional[str] = None, limit: Optional[int] = None, newest_first: bool = False) -> List[Dict[str, Any]]:
        """
        List emails within a date range using in-memory index.

        Args:
            start_date: "YYYY-MM-DD" start date inclusive (user's timezone)
            end_date: "YYYY-MM-DD" end date inclusive (user's timezone)
            timezone: IANA timezone name
            sidecar_missing: Only include emails missing this sidecar
            limit: Max results to return
            newest_first: Sort newest first (default: oldest first)

        Returns:
            List of {"id": msg_id, "date": datetime} dicts
        """
        start_utc, end_utc = self._date_range_to_utc(start_date, end_date, timezone)
        index = self._get_id_index()

        matches = []
        for msg_id, prefix in index.items():
            # Half-open interval: start <= prefix < end
            if prefix < start_utc or prefix >= end_utc:
                continue

            if sidecar_missing:
                sidecar_path = self.root / f"{prefix}_{msg_id}.{sidecar_missing}"
                if sidecar_path.exists():
                    continue

            matches.append((prefix, msg_id))

        # Sort by prefix (date)
        matches.sort(key=lambda x: x[0], reverse=newest_first)

        if limit:
            matches = matches[:limit]

        results = []
        for prefix, msg_id in matches:
            try:
                dt = datetime.strptime(prefix, "%Y%m%d-%H%M%S")
                results.append({"id": msg_id, "date": dt})
            except:
                continue

        return results

    def get(self, message_id: str, include_content: bool = False) -> Optional[Dict[str, Any]]:
        index = self._get_id_index()
        if message_id not in index:
            return None
        meta_path, body_path = self._get_paths(message_id)
        data = {}
        with open(meta_path, "r", encoding="utf-8") as f:
            msg = HeaderParser().parse(f)
            for k in set(msg.keys()):
                vals = msg.get_all(k)
                data[k.lower()] = vals[0] if len(vals) == 1 else vals
        if include_content and body_path.exists():
            with open(body_path, "r", encoding="utf-8") as f:
                data.update(json.load(f))
        return data

    def clear_sidecars(self, key: str, start_date: str, end_date: str, timezone: str) -> Dict[str, Any]:
        """Clear sidecars by key for emails within a date range.

        Args:
            key: Sidecar key to clear (e.g., "analysis.json")
            start_date: "YYYY-MM-DD" start date inclusive (user's timezone)
            end_date: "YYYY-MM-DD" end date inclusive (user's timezone)
            timezone: IANA timezone name

        Returns:
            {
                "success": true,
                "count": N,          # Number of sidecars removed
                "first": "datetime", # Earliest email (ISO 8601 in specified timezone), null if none
                "last": "datetime"   # Latest email (ISO 8601 in specified timezone), null if none
            }
        """
        from datetime import date, time, timedelta

        tz = ZoneInfo(timezone)
        start_d = date.fromisoformat(start_date)
        end_d = date.fromisoformat(end_date)

        start_utc_str, end_utc_str = self._date_range_to_utc(start_date, end_date, timezone)

        # For glob optimization, get the UTC date prefixes that could match
        start_dt = datetime.combine(start_d, time.min, tzinfo=tz).astimezone(ZoneInfo("UTC"))
        end_dt = datetime.combine(end_d + timedelta(days=1), time.min, tzinfo=tz).astimezone(ZoneInfo("UTC"))
        utc_prefixes = {start_dt.strftime("%Y%m%d"), end_dt.strftime("%Y%m%d")}

        deleted = 0
        first_utc: Optional[datetime] = None
        last_utc: Optional[datetime] = None

        for prefix in utc_prefixes:
            for path in self.root.glob(f"{prefix}*.{key}"):
                try:
                    base = path.name[:-(len(key) + 1)]  # "20260121-150000_abc123"
                    dt_part = base.split("_")[0]

                    # Half-open interval: start <= prefix < end
                    if dt_part < start_utc_str or dt_part >= end_utc_str:
                        continue

                    file_dt = datetime.strptime(dt_part, "%Y%m%d-%H%M%S").replace(tzinfo=ZoneInfo("UTC"))
                    os.remove(path)
                    deleted += 1

                    if first_utc is None or file_dt < first_utc:
                        first_utc = file_dt
                    if last_utc is None or file_dt > last_utc:
                        last_utc = file_dt
                except (ValueError, IndexError):
                    continue

        # Convert first/last to user's timezone for response
        first_local = first_utc.astimezone(tz).isoformat() if first_utc else None
        last_local = last_utc.astimezone(tz).isoformat() if last_utc else None

        return {
            "success": True,
            "count": deleted,
            "first": first_local,
            "last": last_local
        }
