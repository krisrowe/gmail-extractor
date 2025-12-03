#!/bin/bash
# This script searches for emails using a Gmail query and creates a CSV file with the metadata.

set -e

# --- Configuration & Arguments ---
GMAIL_QUERY=${1}
CSV_FILE_PATH=${2}

# --- Pre-flight Checks ---
if [ -z "$GMAIL_QUERY" ] || [ -z "$CSV_FILE_PATH" ]; then
    echo "Error: Both a Gmail query and an output CSV file path are required."
    echo "Usage: ./search_to_csv.sh \"<gmail_query>\" <output_csv_file_path>"
    echo "Example: ./search_to_csv.sh \"label:my-label\" my_emails_metadata.csv"
    exit 1
fi

if ! command -v gwsa &> /dev/null; then
    echo "Error: 'gwsa' command not found. Please ensure gworkspace-access is installed and in your PATH."
    exit 1
fi

echo "Starting email search with query: $GMAIL_QUERY"
echo "Output CSV file: $CSV_FILE_PATH"

# --- Search Phase ---
echo "Fetching search results from Gmail (up to 500)..."
SEARCH_RESULTS=$(gwsa mail search "$GMAIL_QUERY" --max-results 500)

# Check if any results were returned
if [ -z "$SEARCH_RESULTS" ] || [ "$(echo "$SEARCH_RESULTS" | jq 'length')" -eq 0 ]; then
    echo "No messages found for the query: $GMAIL_QUERY"
    exit 0
fi

# --- File Creation Phase ---

# Create the CSV file
echo "Creating metadata CSV file: $CSV_FILE_PATH"
# Header
echo "Date,Message ID,Thread ID,From,To,Subject" > "$CSV_FILE_PATH"
# Body (using jq to format as CSV)
echo "$SEARCH_RESULTS" | jq -r '.[] | [.date, .id, .threadId, .from, .to, (if .subject == "N/A" then "" else .subject end)] | @csv' >> "$CSV_FILE_PATH"

echo "---"
echo "Search and CSV creation complete."
echo "  - Metadata saved to: $CSV_FILE_PATH"
echo "Next step: Convert the CSV to JSON using 'csv_to_json.sh'."
