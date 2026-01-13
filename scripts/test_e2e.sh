#!/bin/bash
set -e

ROOT_DIR=$(pwd)
DATA_DIR="$ROOT_DIR/temp_e2e_data"
rm -rf "$DATA_DIR" && mkdir -p "$DATA_DIR"

# Handle Verbosity
REDIRECT="> /dev/null 2>&1"
if [ "$VERBOSE" = "1" ]; then REDIRECT=""; fi

echo "--- Starting E2E Docker Test ---"

# 1. First Pass
echo -n ">> Pass 1: Fetching 2 emails... "
eval "EMAIL_ARCHIVE_DATA_DIR=$DATA_DIR GMEX_LIMIT=2 make fetch $REDIRECT"

METAS1=$(ls "$DATA_DIR"/*.meta 2>/dev/null | wc -l)
BODIES1=$(ls "$DATA_DIR"/*.body 2>/dev/null | wc -l)
if [ "$METAS1" -ne 2 ] || [ "$BODIES1" -ne 2 ]; then STATUS1="❌ FAIL"; else STATUS1="✅ OK"; fi
echo "$STATUS1"

# 2. Second Pass (Incremental)
echo -n ">> Pass 2: Fetching 5 emails (expecting incremental skip)... "
LOGS=$(EMAIL_ARCHIVE_DATA_DIR="$DATA_DIR" GMEX_LIMIT=5 make fetch 2>&1)

if echo "$LOGS" | grep -q "New: 3"; then STATUS2="✅ OK"; else STATUS2="❌ FAIL"; fi
echo "$STATUS2"

METAS2=$(ls "$DATA_DIR"/*.meta 2>/dev/null | wc -l)
BODIES2=$(ls "$DATA_DIR"/*.body 2>/dev/null | wc -l)

# 3. Final Summary Table
echo -e "
--- Test Summary ---"
printf "| %-10s | %-6s | %-6s | %-10s |
" "Pass" "Meta" "Body" "Status"
printf "| %-10s | %-6s | %-6s | %-10s |
" "----------" "------" "------" "----------"
printf "| %-10s | %-6s | %-6s | %-10s |
" "1 (Init)" "$METAS1" "$BODIES1" "$STATUS1"
printf "| %-10s | %-6s | %-6s | %-10s |
" "2 (Incr)" "$METAS2" "$BODIES2" "$STATUS2"
echo "--------------------"

if [[ "$STATUS1" == *"FAIL"* ]] || [[ "$STATUS2" == *"FAIL"* ]]; then exit 1; fi

echo -e "
✅ SUCCESS! E2E Verified."
rm -rf "$DATA_DIR"
