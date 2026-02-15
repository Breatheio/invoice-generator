#!/usr/bin/env python3
"""
Local development server for testing the AI Invoice feature.
Serves static files and proxies API requests to Claude.

Usage:
  1. Set your API key: export ANTHROPIC_API_KEY=sk-ant-...
  2. Run: python3 local-server.py
  3. Open: http://localhost:8080
"""

import http.server
import json
import os
import urllib.request
import urllib.error
from http.server import HTTPServer, SimpleHTTPRequestHandler

PORT = 8080
API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')

class LocalDevHandler(SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/api/parse-invoice':
            self.handle_parse_invoice()
        else:
            self.send_error(404, 'Not Found')

    def handle_parse_invoice(self):
        # Read request body
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        try:
            data = json.loads(body)
            prompt = data.get('prompt', '')
        except json.JSONDecodeError:
            self.send_json_error(400, 'Invalid JSON')
            return

        if not prompt or len(prompt.strip()) < 5:
            self.send_json_error(400, 'Prompt too short')
            return

        if not API_KEY:
            self.send_json_error(500, 'ANTHROPIC_API_KEY not set. Run: export ANTHROPIC_API_KEY=sk-ant-...')
            return

        # Sanitize prompt
        sanitized_prompt = prompt.strip()[:500]

        # Call Claude API
        system_prompt = """You are an invoice data extractor. Parse the user's natural language request and extract invoice information. Return ONLY valid JSON with this exact structure:

{
  "client": {
    "name": "string or null",
    "email": "string or null",
    "address": "string or null"
  },
  "items": [
    {
      "description": "string",
      "quantity": number,
      "price": number
    }
  ],
  "invoice": {
    "notes": "string or null"
  }
}

Rules:
- Extract client name, email if mentioned
- Parse line items with description, quantity, and unit price
- For hourly rates like "$75/hour for 8 hours", set quantity=8 and price=75
- For total amounts like "$500 for web design", set quantity=1 and price=500
- For multiple items like "3 widgets at $25 each", set quantity=3 and price=25
- Always return valid JSON, nothing else
- If you can't parse something, use null for optional fields
- Always include at least one item"""

        request_body = json.dumps({
            'model': 'claude-3-haiku-20240307',
            'max_tokens': 1024,
            'system': system_prompt,
            'messages': [{'role': 'user', 'content': sanitized_prompt}]
        }).encode('utf-8')

        req = urllib.request.Request(
            'https://api.anthropic.com/v1/messages',
            data=request_body,
            headers={
                'Content-Type': 'application/json',
                'x-api-key': API_KEY,
                'anthropic-version': '2023-06-01'
            }
        )

        try:
            with urllib.request.urlopen(req) as response:
                api_response = json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            print(f'Claude API error: {e.code} - {error_body}')
            self.send_json_error(500, 'Failed to process your request. Please try again.')
            return
        except Exception as e:
            print(f'Request error: {e}')
            self.send_json_error(500, 'Connection failed. Check your internet and try again.')
            return

        # Extract text content
        text_content = None
        for content in api_response.get('content', []):
            if content.get('type') == 'text':
                text_content = content.get('text', '')
                break

        if not text_content:
            self.send_json_error(500, 'Invalid response from AI')
            return

        # Parse JSON from response
        try:
            json_text = text_content.strip()
            if json_text.startswith('```json'):
                json_text = json_text[7:]
            elif json_text.startswith('```'):
                json_text = json_text[3:]
            if json_text.endswith('```'):
                json_text = json_text[:-3]
            json_text = json_text.strip()

            parsed_data = json.loads(json_text)
        except json.JSONDecodeError:
            print(f'Failed to parse: {text_content}')
            self.send_json_error(500, "I couldn't understand that. Try: 'Invoice [name] for [amount] [service]'")
            return

        # Validate and normalize
        if not parsed_data.get('items') or not isinstance(parsed_data['items'], list):
            self.send_json_error(400, "I couldn't identify any items. Try: 'Invoice Bob for $500 web design'")
            return

        # Normalize items
        parsed_data['items'] = [
            {
                'description': item.get('description', 'Service'),
                'quantity': float(item.get('quantity', 1)),
                'price': float(item.get('price', 0))
            }
            for item in parsed_data['items']
        ]

        # Ensure client object
        client = parsed_data.get('client', {})
        parsed_data['client'] = {
            'name': client.get('name'),
            'email': client.get('email'),
            'address': client.get('address')
        }

        # Ensure invoice object
        invoice = parsed_data.get('invoice', {})
        parsed_data['invoice'] = {
            'notes': invoice.get('notes')
        }

        # Send success response
        self.send_json_response(200, parsed_data)

    def send_json_response(self, status, data):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def send_json_error(self, status, message):
        self.send_json_response(status, {'error': message})

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def end_headers(self):
        self.send_header('Cache-Control', 'no-cache')
        super().end_headers()


if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    print(f'\n🚀 Local Invoice Generator Server')
    print(f'=' * 40)
    print(f'Server:  http://localhost:{PORT}')
    print(f'API Key: {"✓ Set" if API_KEY else "✗ NOT SET"}')

    if not API_KEY:
        print(f'\n⚠️  To test AI features, set your API key:')
        print(f'   export ANTHROPIC_API_KEY=sk-ant-...')

    print(f'\nPress Ctrl+C to stop\n')

    server = HTTPServer(('localhost', PORT), LocalDevHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n\nServer stopped.')
