import pytest
import json
from pathlib import Path
from datetime import datetime
from email_archive import EmailStore

# Sociable Unit Test for 'sidecar' management.
# Verifies that processing metadata can be linked, verified, and retrieved.

def test_sidecar_lifecycle(tmp_path):
    store = EmailStore(tmp_path)
    
    # 1. Setup email
    msg_id = "lifecycle_test"
    date = datetime(2026, 1, 12, 15, 0, 0)
    store.save(msg_id, date, {"Subject": "Main"}, {"body": "Content"})
    
    # 2. Initially no sidecar
    # Use the new discovery logic
    items = store.list(sidecar_missing="processed.json")
    assert len(items) == 1
    
    # 3. Save sidecar
    processing_data = {"status": "success", "engine": "gemini"}
    store.save_sidecar(msg_id, "processed.json", processing_data)
    
    # 4. Verify existence via list filtering
    items_after = store.list(sidecar_missing="processed.json")
    assert len(items_after) == 0
    
    # 5. Retrieve and verify content
    loaded = store.get_sidecar(msg_id, "processed.json")
    assert loaded["status"] == "success"
    assert loaded["engine"] == "gemini"

def test_sidecar_text_retrieval(tmp_path):
    store = EmailStore(tmp_path)
    msg_id = "text_test"
    store.save(msg_id, datetime.now(), {}, {})
    
    # Save a non-json sidecar
    store.save_sidecar(msg_id, "status.txt", "OK")
    
    assert store.get_sidecar(msg_id, "status.txt") == "OK"