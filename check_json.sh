#!/bin/bash
# This script checks a JSON file and reports the total number of emails
# and how many of them have a populated body.

set -e

# --- Configuration & Arguments ---
JSON_FILE=${1}

# --- Pre-flight Checks ---
if [ -z "$JSON_FILE" ]; then
    echo "Error: Path to the JSON file is required."
    echo "Usage: ./check_json.sh <path_to_json_file>"
    exit 1
fi
if [ ! -f "$JSON_FILE" ]; then
    echo "Error: JSON file not found at '$JSON_FILE'"
    exit 1
fi

# --- Analysis Phase ---
echo "Analyzing '$JSON_FILE'..."

TOTAL_COUNT=$(jq 'length' "$JSON_FILE")
POPULATED_COUNT=$(jq '[.[] | select(.body | type == "object")] | length' "$JSON_FILE")
UNPOPULATED_COUNT=$(jq '[.[] | select(.body | type == "string")] | length' "$JSON_FILE")
NON_EMPTY_SUBJECT_COUNT=$(jq '[.[] | select(.subject and .subject != "")] | length' "$JSON_FILE")

# Extract all dates, convert them to a sortable format, then get the earliest and latest.
# This approach is more robust than a simple string sort.
# We create a temporary file to hold the dates to avoid issues with large datasets.
TEMP_DATES_FILE=$(mktemp)
jq -r '.[].date' "$JSON_FILE" > "$TEMP_DATES_FILE"

# The `date -d` command can parse the date strings. We format them as YYYY-MM-DD HH:MM:SS
# and then sort. We use a pipe to separate the sortable key from the original date.
LATEST_DATE=$(cat "$TEMP_DATES_FILE" | while IFS= read -r d; do if [ -n "$d" ]; then echo "$(date -d "$d" +'%Y-%m-%d %H:%M:%S')|$d"; fi; done | sort -r | head -n 1 | cut -d'|' -f2-)
EARLIEST_DATE=$(cat "$TEMP_DATES_FILE" | while IFS= read -r d; do if [ -n "$d" ]; then echo "$(date -d "$d" +'%Y-%m-%d %H:%M:%S')|$d"; fi; done | sort | head -n 1 | cut -d'|' -f2-)

rm "$TEMP_DATES_FILE"

echo "---"
echo "JSON file analysis:"
echo "  - Total email objects: $TOTAL_COUNT"
echo "  - Bodies populated (object): $POPULATED_COUNT"
echo "  - Bodies not populated (string): $UNPOPULATED_COUNT"
echo "  - Emails with non-empty subject: $NON_EMPTY_SUBJECT_COUNT"
echo "  - Latest email date: $LATEST_DATE"
echo "  - Earliest email date: $EARLIEST_DATE"
echo "---"
