#!/bin/bash
# This script intelligently updates message bodies in a given JSON file.
# It operates in two stages: Analysis and Execution, and supports a --dry-run flag.

set -e

# --- Argument Parsing ---
DRY_RUN=false
JSON_FILE=""
LIMIT=""
# Parse command-line arguments
ARGS=()
while [[ $# -gt 0 ]]; do
  case $1 in
    --dry-run)
      DRY_RUN=true
      shift # past argument
      ;;
    *)
      ARGS+=("$1") # save positional arg
      shift # past argument
      ;;
  esac
done
set -- "${ARGS[@]}" # restore positional arguments

JSON_FILE=${1}
LIMIT=${2}

# The path to the helper Python script, assumed to be in the same directory.
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
UPDATE_SCRIPT="$SCRIPT_DIR/update_json_body.py"


# --- Pre-flight Checks ---
if [ -z "$JSON_FILE" ]; then
    echo "Error: Path to the JSON file is required."
    echo "Usage: ./update_bodies.sh <path_to_json_file> [limit] [--dry-run]"
    exit 1
fi
if [ ! -f "$JSON_FILE" ]; then
    echo "Error: JSON file not found at '$JSON_FILE'"
    exit 1
fi
if [ ! -x "$UPDATE_SCRIPT" ]; then
    echo "Error: Update script not found or not executable at '$UPDATE_SCRIPT'"
    exit 1
fi
if ! command -v gwsa &> /dev/null; then
    echo "Error: 'gwsa' command not found. Please ensure gworkspace-access is installed and in your PATH."
    exit 1
fi

# Get initial file size for comparison
INITIAL_FILE_SIZE=$(ls -lh "$JSON_FILE" | awk '{print $5}')


# --- Stage 1: Analysis and Planning ---
echo "--- Stage 1: Analysis and Planning ---"
echo "Analyzing '$JSON_FILE'..."

IDS_TO_UPDATE=$(jq -r '.[] | select(.body | type == "string") | .id' "$JSON_FILE")
TOTAL_COUNT=$(jq 'length' "$JSON_FILE")
INITIAL_PROCESSED_COUNT=$(jq '[.[] | select(.body | type == "object")] | length' "$JSON_FILE")

if [ -z "$IDS_TO_UPDATE" ]; then
    UNPROCESSED_COUNT=0
else
    UNPROCESSED_COUNT=$(echo "$IDS_TO_UPDATE" | wc -l)
fi

# Determine the list of IDs to process for this run
if [ -z "$IDS_TO_UPDATE" ]; then
    IDS_TO_PROCESS=()
elif [ -n "$LIMIT" ] && [ "$LIMIT" -ge 0 ]; then
    mapfile -t IDS_TO_PROCESS < <(echo "$IDS_TO_UPDATE" | head -n "$LIMIT")
else
    mapfile -t IDS_TO_PROCESS < <(echo "$IDS_TO_UPDATE")
fi
NUM_TO_PROCESS=${#IDS_TO_PROCESS[@]}


echo
echo "Execution Plan:"
echo "  - Total messages in JSON: $TOTAL_COUNT"
echo "  - Already processed: $INITIAL_PROCESSED_COUNT"
echo "  - To be processed in this run: $NUM_TO_PROCESS"
if [ "$NUM_TO_PROCESS" -gt 0 ]; then
    echo "  - IDs to be processed:"
    for id in "${IDS_TO_PROCESS[@]}"; do
        echo "    - $id"
    done
else
    echo "  - All messages have already been processed."
fi
echo

# --- Dry Run Check ---
if [ "$DRY_RUN" = true ]; then
    echo "Dry run enabled. Exiting before Stage 2."
    exit 0
fi

# --- Stage 2: Execution ---
echo "--- Stage 2: Execution ---"

if [ "$NUM_TO_PROCESS" -eq 0 ]; then
    echo "No messages to process in this run."
    if [ "$UNPROCESSED_COUNT" -eq 0 ]; then
        echo "All message bodies are already in the correct format."
    fi
    exit 0
fi

PROCESSED_DATES=()
PROCESSED_IDS=()
PROCESSED_LENGTHS=()
PROCESSED_SUBJECTS=()
PROCESSED_IN_RUN=0

for message_id in "${IDS_TO_PROCESS[@]}"; do
    if [ -z "$message_id" ]; then
        continue
    fi

    PROCESSED_IN_RUN=$((PROCESSED_IN_RUN + 1))
    echo "--- Processing message ${PROCESSED_IN_RUN} of ${NUM_TO_PROCESS}: $message_id ---"

    echo "Fetching full message payload from Gmail..."
    message_payload_json=$(gwsa mail read "$message_id")

    if [ -z "$message_payload_json" ]; then
        echo "Warning: Failed to fetch payload for message ID '$message_id'. Skipping."
        continue
    fi

    # Extract info for reporting
    EMAIL_DATE=$(echo "$message_payload_json" | jq -r '.date')
    BODY_LENGTH=$(echo "$message_payload_json" | jq -r '.body.text | length')
    EMAIL_SUBJECT=$(echo "$message_payload_json" | jq -r '.subject // "N/A"')

    echo "Updating the 'body' field in '$JSON_FILE'..."
    "$UPDATE_SCRIPT" "$JSON_FILE" "$message_id" "$message_payload_json"

    PROCESSED_DATES+=("$EMAIL_DATE")
    PROCESSED_IDS+=("$message_id")
    PROCESSED_LENGTHS+=("$BODY_LENGTH")
    PROCESSED_SUBJECTS+=("$EMAIL_SUBJECT")
done

# --- Post-run Summary ---
echo
echo "Run Summary:"

if [ "$PROCESSED_IN_RUN" -gt 0 ]; then
    echo
    echo "--- Updated Messages (This Run) ---"
    printf "% -22s | % -35s | % -30s | %s\n" "Message ID" "Datetime" "Subject" "Body Length"
    printf '%s\n' "--------------------------------------------------------------------------------------------------------------------"
    for i in "${!PROCESSED_IDS[@]}"; do
        # Truncate subject for display if it's too long
        SUBJECT_DISPLAY="${PROCESSED_SUBJECTS[$i]}"
        if [ ${#SUBJECT_DISPLAY} -gt 30 ]; then
            SUBJECT_DISPLAY="${SUBJECT_DISPLAY:0:27}..."
        fi
        printf "% -22s | % -35s | % -30s | %s chars\n" "${PROCESSED_IDS[$i]}" "${PROCESSED_DATES[$i]}" "$SUBJECT_DISPLAY" "${PROCESSED_LENGTHS[$i]}"
    done
    printf '%s\n\n' "--------------------------------------------------------------------------------------------------------------------"

    # Convert dates to a sortable format, sort them, and extract the original date strings
    SORTED_DATES_LINES=$(printf "%s\n" "${PROCESSED_DATES[@]}" | while IFS= read -r d; do if [ -n "$d" ]; then echo "$(date -d "$d" +'%Y-%m-%d %H:%M:%S')|$d"; fi; done | sort)
    
    EARLIEST_PROCESSED_DATE=$(echo "$SORTED_DATES_LINES" | head -n 1 | cut -d'|' -f2-)
    LATEST_PROCESSED_DATE=$(echo "$SORTED_DATES_LINES" | tail -n 1 | cut -d'|' -f2-)

    echo "  - Total message bodies updated in this run: $PROCESSED_IN_RUN"
    echo "  - Earliest email processed: $EARLIEST_PROCESSED_DATE"
    echo "  - Latest email processed:   $LATEST_PROCESSED_DATE"
else
    echo "  - No message bodies were updated in this run."
fi

FINAL_FILE_SIZE=$(ls -lh "$JSON_FILE" | awk '{print $5}')
echo
echo "--- File Size ---"
echo "  - Initial size: $INITIAL_FILE_SIZE"
echo "  - Final size:   $FINAL_FILE_SIZE"
echo 


# Final verification
echo "Verifying final counts..."
FINAL_UNPROCESSED_COUNT=$(jq '[.[] | select(.body | type == "string")] | length' "$JSON_FILE")
if [ "$FINAL_UNPROCESSED_COUNT" -gt 0 ]; then
    echo "$FINAL_UNPROCESSED_COUNT message(s) still need to be updated."
else
    echo "All message bodies have been successfully updated."
fi