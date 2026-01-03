from flask import Flask, request, jsonify
from atlassian import Confluence
import re
import logging
import requests
from vault_utils import VaultManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
URL = "http://57.159.25.203:8090"

try:
    vault = VaultManager()
    USER, PW = vault.get_confluence_credentials()
    confluence = Confluence(url=URL, username=USER, password=PW)
except Exception as e:
    logger.critical(f"Vault error: {e}")
    raise RuntimeError("Vault required")

PATTERNS = {
    'AWS Key': r'AKIA[0-9A-Z]{16}',
    'AWS Secret': r'(?:aws_secret_access_key|AWS_SECRET_ACCESS_KEY)\s*[:=]\s*([A-Za-z0-9/+=]{40})',
    'GitHub Token': r'ghp_[a-zA-Z0-9]{36}',
    'API Key': r'(?:api[_\s-]?key|apikey)\s*[:=]\s*["\']?([a-zA-Z0-9_\-]{8,})["\']?',
    'Password': r'(?:password|passwd|pwd|pass)\s*[:=]\s*["\']?([a-zA-Z0-9!@#$%^&*_\-]{3,})["\']?',
    'SSH Key': r'-----BEGIN (?:RSA|OPENSSH|DSA|EC) PRIVATE KEY-----'
}

def scan_content(content):
    detected = []
    for name, pattern in PATTERNS.items():
        for match in re.finditer(pattern, content, re.IGNORECASE):
            if match.lastindex:
                detected.append({'type': name, 'text': match.group(1), 'start': match.start(1), 'end': match.end(1)})
            else:
                detected.append({'type': name, 'text': match.group(0), 'start': match.start(), 'end': match.end()})
    return detected

def mask_content(content, secrets):
    if not secrets: return content
    sorted_secrets = sorted(secrets, key=lambda x: x['start'], reverse=True)
    for s in sorted_secrets:
        mask = '*' * min(len(s['text']), 20)
        content = content[:s['start']] + mask + content[s['end']:]
    return content

@app.route('/webhook/page-updated', methods=['POST'])
@app.route('/webhook/page-created', methods=['POST'])
def handle_webhook():
    data = request.json
    page_id = data.get('page', {}).get('id') or data.get('content', {}).get('id') or data.get('id')
    if not page_id: return jsonify({'error': 'no id'}), 400
    
    try:
        page = confluence.get_page_by_id(page_id, expand='body.storage,version')
        content = page['body']['storage']['value']
        ver = page['version']['number']
        title = page['title']
        
        secrets = scan_content(content)
        if not secrets: return jsonify({'status': 'clean'}), 200
        
        masked = mask_content(content, secrets)
        
        resp = requests.put(
            f"{URL}/rest/api/content/{page_id}",
            json={
                "version": {"number": ver + 1, "message": "Auto-masked secrets"},
                "title": title, "type": "page",
                "body": {"storage": {"value": masked, "representation": "storage"}}
            },
            auth=(USER, PW),
            headers={"Content-Type": "application/json"}
        )
        return jsonify({'status': 'masked', 'count': len(secrets)}), 200
    except Exception as e:
        logger.error(f"Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health():
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002)
