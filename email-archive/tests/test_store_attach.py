import pytest
import json
from pathlib import Path
from datetime import datetime
from email_archive import EmailStore

# Sociable Unit Test for 'attach' capability.
# Verifies that extended metadata/processing outputs can be linked to emails.

def test_attach_generic_metadata(tmp_path):
    store = EmailStore(tmp_path)
    
    # 1. Setup email
    msg_id = "attach_test"
    date = datetime(2026, 1, 12, 15, 0, 0)
    store.save(msg_id, date, {"Subject": "Main Email"}, {"body": "Content"})
    
    # 2. Attach a generic processing result
    # Format: [ID].ext
    processing_data = {
        "status": "processed",
        "worker_version": "1.0",
        "tags": ["extracted", "verified"]
    }
    
    store.attach(msg_id, "processed.json", processing_data)
    
    # 3. Verify sidecar existence
    # Expected filename: 20260112-150000_attach_test.processed.json
    expected_file = tmp_path / "20260112-150000_attach_test.processed.json"
    assert expected_file.exists()
    
    # 4. Verify content
    with open(expected_file, "r") as f:
        loaded = json.load(f)
        assert loaded["status"] == "processed"
        assert loaded["worker_version"] == "1.0"

def test_attach_raw_text(tmp_path):
    store = EmailStore(tmp_path)
    msg_id = "text_attach"
    store.save(msg_id, datetime.now(), {}, {})
    
    store.attach(msg_id, "checksum.txt", "abc-123-xyz")
    
    # Verify file content is raw text
    matches = list(tmp_path.glob("*_text_attach.checksum.txt"))
    assert len(matches) == 1
    assert matches[0].read_text() == "abc-123-xyz"
