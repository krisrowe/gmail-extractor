#!/usr/bin/env python3
import json
import sys

def update_json_body(json_file_path, message_id, new_content):
    """
    Updates the 'body' of a specific message object in a JSON file.
    """
    try:
        with open(json_file_path, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: JSON file not found at {json_file_path}")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {json_file_path}")
        sys.exit(1)

    message_found = False
    for message in data:
        if message.get('id') == message_id:
            try:
                # The new_content is expected to be a JSON string from gwsa,
                # so we parse it into a Python dictionary.
                message['body'] = json.loads(new_content)
            except json.JSONDecodeError:
                # As a fallback, if it's not valid JSON, store it as a raw string.
                message['body'] = new_content
            message_found = True
            break

    if not message_found:
        print(f"Error: Message with ID '{message_id}' not found in {json_file_path}")
        return

    # Write the updated data back to the file
    with open(json_file_path, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"Successfully updated 'body' for message ID '{message_id}' in {json_file_path}")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: ./update_json_body.py <json_file_path> <message_id> '<json_content>'")
        sys.exit(1)

    file_path_arg = sys.argv[1]
    message_id_arg = sys.argv[2]
    new_content_arg = sys.argv[3]
    update_json_body(file_path_arg, message_id_arg, new_content_arg)
