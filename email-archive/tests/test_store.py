import pytest
import json
import logging
import os
from pathlib import Path
from datetime import datetime
from email_archive import EmailStore

level = os.environ.get("LOG_LEVEL", "WARNING").upper()
logging.basicConfig(level=level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def test_save_and_get_full(tmp_path):
    store = EmailStore(tmp_path)
    msg_id, date = "msg_123", datetime(2026, 1, 12, 10, 0, 0)
    headers, content = {"Subject": "Test"}, {"body_text": "Hello"}
    store.save(msg_id, date, headers, content)
    assert (tmp_path / "20260112-100000_msg_123.meta").exists()
    data = store.get(msg_id, include_content=True)
    assert data["id"] == msg_id and data["body_text"] == "Hello"

def test_save_sidecar(tmp_path):
    store = EmailStore(tmp_path)
    msg_id, date = "msg_sidecar", datetime.now()
    store.save(msg_id, date, {}, {})
    data = {"status": "archived"}
    # Verify the new method name
    store.save_sidecar(msg_id, "processed.json", data)
    assert store.has_sidecar(msg_id, "processed.json")
    loaded = store.get_sidecar(msg_id, "processed.json")
    assert loaded["status"] == "archived"

def test_save_and_get_metadata_only(tmp_path):
    store = EmailStore(tmp_path)
    msg_id, date = "msg_456", datetime.now()
    store.save(msg_id, date, {"Subject": "Meta"}, {"body_text": "Hidden"})
    data = store.get(msg_id, include_content=False)
    assert data["subject"] == "Meta" and "body_text" not in data

def test_list_chronological(tmp_path):
    store = EmailStore(tmp_path)
    d1, d2 = datetime(2026, 1, 1), datetime(2026, 1, 2)
    store.save("b", d2, {}, {})
    store.save("a", d1, {}, {})
    items = store.list()
    assert [i["id"] for i in items] == ["a", "b"]

def test_save_and_retrieve_complex_headers(tmp_path):
    store = EmailStore(tmp_path)
    msg_id = "complex"
    headers = {"Subject": "RE: Test 🌍", "Label": ["W", "U"]}
    store.save(msg_id, datetime.now(), headers, {})
    data = store.get(msg_id)
    assert data["subject"] == "RE: Test 🌍" and len(data["label"]) == 2

def test_atomic_overwrite(tmp_path):
    store = EmailStore(tmp_path)
    msg_id, date = "overwrite", datetime(2026, 1, 1)
    store.save(msg_id, date, {"S": "v1"}, {"v": 1})
    store.save(msg_id, date, {"S": "v2"}, {"v": 2})
    data = store.get(msg_id, include_content=True)
    assert data["s"] == "v2" and data["v"] == 2
