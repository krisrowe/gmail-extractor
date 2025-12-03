# Gmail Extractor: A User Guide

This guide will walk you through setting up and using the Gmail Extractor tool to get your email data into structured formats.

## 1. Initial Setup (One-Time)

This section covers the one-time setup steps required before using the Gmail Extractor.

### 1.1. Install Prerequisites

Ensure you have the following installed on your system:

-   **Python 3** (Recommended: 3.11 or higher).
-   **`jq`**: A lightweight and flexible command-line JSON processor.
    -   `sudo apt-get install jq` (for Debian/Ubuntu)
    -   `brew install jq` (for macOS)
-   **[`gworkspace-access` (`gwsa`)](https://github.com/krisrowe/gworkspace-access)**: This tool is essential for communicating with the Gmail API.
    1.  **Installation**: Follow the installation instructions in the `gworkspace-access` repository. The recommended way is using `pipx`:
        ```bash
        pipx install git+https://github.com/krisrowe/gworkspace-access.git
        ```
    2.  **Authentication**: `gwsa` requires authentication to access your Gmail account. Some Gmail accounts might not fully support Application Default Credentials (ADC) for all operations. For simplicity in this local setup, it's often more straightforward to use **Custom OAuth Client ID**.

        -   **Custom OAuth Client ID**: Obtain `client_secrets.json` from your Google Cloud Project (API & Services -> Credentials -> OAuth 2.0 Client IDs -> Desktop App). Place this file in `~/.config/gworkspace-access/client_secrets.json`.
        -   **Application Default Credentials (ADC)**: Authenticate your `gcloud` CLI with the necessary scopes:
            ```bash
            gcloud auth application-default login --scopes=https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/gmail.modify,https://www.googleapis.com/auth/drive.file
            ```

        Please refer to the [official `gworkspace-access` repository](https://github.com/krisrowe/gworkspace-access) for detailed instructions on both authentication methods. You *must* successfully run `gwsa setup` before proceeding, making sure `client_secrets.json` is correctly placed or passed.

### 1.2. Verify `gwsa` Setup

After installing and authenticating `gwsa`, run the following command to ensure it's properly configured:

```bash
gwsa setup --status
```
You should see output indicating that `gwsa is fully configured and ready to use`.

## 2. End-to-End Usage Guide

This section guides you through the process of extracting your Gmail data. We will use the example of extracting emails with the label "Sasha".

### 2.1. Step 1: Search for Emails and Create CSV

This step searches your Gmail for messages matching your query and saves their metadata (Date, ID, From, To, Subject) into a CSV file.

**Action:**
```bash
./search_to_csv.sh "label:Sasha" sasha_emails_metadata.csv
```

**Review:**
-   Check the console output to confirm that the expected number of messages were found (e.g., "Found 48 messages").
-   Open `sasha_emails_metadata.csv` to ensure the data looks correct. Verify that blank subjects are truly empty and not "N/A".

### 2.2. Step 2: Convert CSV to Initial JSON

This step converts the CSV metadata into a JSON file. Initially, the 'body' field for each email in the JSON will be a placeholder ("pending").

**Action:**
```bash
./csv_to_json.sh sasha_emails_metadata.csv sasha_emails_full_content.json
```

**Review:**
-   Check the console output. It should report how many data rows were found in the CSV and how many JSON objects were written.
-   Run the `check_json.sh` script to verify the initial state of your JSON file:
    ```bash
    ./check_json.sh sasha_emails_full_content.json
    ```
    You should see:
    -   `Total email objects: 48`
    -   `Bodies populated (object): 0`
    -   `Bodies not populated (string): 48`
    -   Correct earliest and latest dates.
    -   Correct count of emails with non-empty subjects.

### 2.3. Step 3: Populate Email Bodies (Initial Test Run)

This step updates the JSON file by fetching the full content of each email from Gmail. We will perform a small test run first.

**Action (Dry Run):**
First, run a dry run to see the plan without processing any messages:
```bash
./update_bodies.sh sasha_emails_full_content.json --dry-run
```
**Review:**
-   The output should show the execution plan and confirm "Dry run enabled. Exiting before Stage 2."

**Action (Process 3 Messages):**
Now, process the first 3 messages:
```bash
./update_bodies.sh sasha_emails_full_content.json 3
```
**Review:**
-   Observe the detailed output for each processed message, including its ID, datetime, subject, and body length.
-   Review the "Run Summary" for the processed counts, date range, and file size changes.
-   Run `check_json.sh` again to confirm the updated counts:
    ```bash
    ./check_json.sh sasha_emails_full_content.json
    ```
    You should now see:
    -   `Bodies populated (object): 3`
    -   `Bodies not populated (string): 45`

### 2.4. Step 4: Populate Remaining Email Bodies

Once you are satisfied with the test run, you can process the rest of the emails.

**Action:**
```bash
./update_bodies.sh sasha_emails_full_content.json
```

**Review:**
-   The output should show all remaining messages being processed.
-   Review the "Run Summary" for the processed counts, date range, and file size changes.
-   Run `check_json.sh` one last time:
    ```bash
    ./check_json.sh sasha_emails_full_content.json
    ```
    You should now see:
    -   `Bodies populated (object): 48`
    -   `Bodies not populated (string): 0`

## 3. Scripts Overview

-   **`search_to_csv.sh`**: Searches Gmail and creates a CSV file of metadata.
-   **`csv_to_json.sh`**: Converts a CSV metadata file into a JSON file with placeholder bodies.
-   **`update_bodies.sh`**: Fetches full email bodies via `gwsa` and updates the JSON file.
-   **`update_json_body.py`**: Helper script for `update_bodies.sh` to update individual JSON entries.
-   **`check_json.sh`**: Analyzes a JSON file, reporting counts and date ranges.