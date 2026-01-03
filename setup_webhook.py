import requests
import json
import sys
from vault_utils import VaultManager

# Config
CONF_URL = "http://57.159.25.203:8090"
SCANNER_URL = "http://127.0.0.1:5002"

try:
    vault = VaultManager()
    USER, PW = vault.get_confluence_credentials()
except Exception as e:
    print(f"Vault failed: {e}")
    sys.exit(1)

def create_hook(event, endpoint):
    data = {
        "name": f"Scanner - {event}",
        "url": f"{SCANNER_URL}{endpoint}",
        "events": [event],
        "active": True
    }
    r = requests.post(
        f"{CONF_URL}/rest/api/webhooks",
        auth=(USER, PW),
        headers={"Content-Type": "application/json"},
        json=data
    )
    if r.status_code == 201:
        print(f"Hook created: {event}")
    else:
        print(f"Failed: {r.status_code} {r.text}")

def list_hooks():
    r = requests.get(f"{CONF_URL}/rest/api/webhooks", auth=(USER, PW))
    if r.status_code == 200:
        res = r.json().get('results', [])
        for h in res:
            print(f"- {h['name']}: {h['url']}")
        return res
    return []

if __name__ == "__main__":
    print("Checking Hooks...")
    existing = list_hooks()
    
    if any('Scanner' in h['name'] for h in existing):
        print("Hooks already exist.")
    else:
        create_hook("page_created", "/webhook/page-created")
        create_hook("page_updated", "/webhook/page-updated")
    print("Done.")
