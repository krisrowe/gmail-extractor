#!/bin/bash
set -e

ROOT_DIR=$(pwd)
DATA_DIR="$ROOT_DIR/temp_e2e_data"
rm -rf "$DATA_DIR" && mkdir -p "$DATA_DIR"

echo "--- Starting E2E Docker Test ---"
echo "Data Dir: $DATA_DIR"

# 1. First Pass
echo -e "\n>> Pass 1: Fetching first 2 emails..."
EMAIL_ARCHIVE_DATA_DIR="$DATA_DIR" GMEX_LIMIT=2 make fetch

FILES=$(ls "$DATA_DIR"/*.meta | wc -l)
echo "Pass 1 complete. Files found: $FILES"
if [ "$FILES" -ne 2 ]; then
  echo "❌ FAILED: Expected 2 files, found $FILES"
  exit 1
fi

# 2. Second Pass (Incremental)
echo -e "\n>> Pass 2: Fetching 5 emails (expecting incremental skip)..."
# Capture output to check for "New: 3"
LOGS=$(EMAIL_ARCHIVE_DATA_DIR="$DATA_DIR" GMEX_LIMIT=5 make fetch 2>&1)
echo "$LOGS"

if echo "$LOGS" | grep -q "New: 3"; then
  echo -e "\n✅ IDEMPOTENCY VERIFIED: Logs confirmed 3 new messages."
  echo "✅ SUCCESS! E2E Incremental Sync Verified."
else
  echo -e "\n❌ FAILED: Incremental sync logic did not report expected new count."
  exit 1
fi

# 3. Cleanup
echo -e "\nCleaning up..."
rm -rf "$DATA_DIR"
echo "Done."
