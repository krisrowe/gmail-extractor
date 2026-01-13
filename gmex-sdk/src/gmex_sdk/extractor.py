import json
import os
import logging
import base64
from typing import List, Dict, Any, Optional

from googleapiclient.discovery import build
from .config import resolve_credentials, get_extract_setting

logger = logging.getLogger(__name__)

class GmailExtractor:
    """
    SDK for extracting emails from Gmail using direct Google APIs.
    """
    def __init__(self):
        self._service = None

    def _get_service(self):
        if self._service:
            return self._service
            
        creds = resolve_credentials()
        if creds:
            self._service = build('gmail', 'v1', credentials=creds)
            return self._service
        return None

    def check_auth(self) -> bool:
        """Verify API connectivity."""
        try:
            return self._get_service() is not None
        except:
            return False

    def search(self, query: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Search Gmail and return metadata-only results.
        """
        if query is None:
            query = get_extract_setting("query", "in:inbox")
        if limit is None:
            limit = int(get_extract_setting("limit", 50))

        service = self._get_service()
        if not service:
            raise RuntimeError("Not authenticated. Use 'gmex token import' or set GOOGLE_APPLICATION_CREDENTIALS.")

        logger.info(f"Direct API Search: '{query}' (Limit: {limit})")
        
        # 1. Search IDs
        results = service.users().messages().list(userId='me', q=query, maxResults=limit).execute()
        summaries = results.get('messages', [])
        
        if not summaries:
            return []

        # 2. Batch Metadata (Minimal headers for performance)
        messages = []
        for s in summaries:
            msg = service.users().messages().get(
                userId='me', 
                id=s['id'], 
                format='metadata',
                metadataHeaders=['Subject', 'From', 'To', 'Date']
            ).execute()
            
            headers = {h['name'].lower(): h['value'] for h in msg.get('payload', {}).get('headers', [])}
            messages.append({
                "id": msg['id'],
                "threadId": msg['threadId'],
                "date": headers.get('date'),
                "from": headers.get('from'),
                "to": headers.get('to'),
                "subject": headers.get('subject'),
                "labelIds": msg.get('labelIds', [])
            })
        return messages

    def get_message(self, message_id: str) -> Dict[str, Any]:
        """Fetch full message content."""
        service = self._get_service()
        if not service:
            raise RuntimeError("Not authenticated.")
            
        msg = service.users().messages().get(userId='me', id=message_id, format='full').execute()
        headers = {h['name'].lower(): h['value'] for h in msg.get('payload', {}).get('headers', [])}
        
        def get_body(payload):
            body = {'text': '', 'html': ''}
            if 'parts' in payload:
                for part in payload['parts']:
                    res = get_body(part)
                    body['text'] += res['text']
                    body['html'] += res['html']
            else:
                mime_type = payload.get('mimeType')
                data = payload.get('body', {}).get('data', '')
                if data:
                    decoded = base64.urlsafe_b64decode(data).decode('utf-8', errors='replace')
                    if mime_type == 'text/plain': body['text'] = decoded
                    elif mime_type == 'text/html': body['html'] = decoded
            return body

        return {
            "id": msg['id'],
            "threadId": msg['threadId'],
            "labelIds": msg.get('labelIds', []),
            "snippet": msg.get('snippet'),
            "date": headers.get('date'),
            "from": headers.get('from'),
            "to": headers.get('to'),
            "subject": headers.get('subject'),
            "body": get_body(msg.get('payload', {})),
            "attachments": [] 
        }
