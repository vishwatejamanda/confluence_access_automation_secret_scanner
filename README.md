# Confluence Automation

This project handles automatic user access and space setup for Confluence. I've also added a secret scanner that runs on webhooks to mask passwords or keys if they get pasted into pages.

Everything is running on the Azure VM (57.159.25.203).

### Main Links
* Dashboard: http://57.159.25.203:5001
* Vault UI: http://57.159.25.203:8200 (Token: my-root-token)

---

### How it works

#### 1. User Access
It takes requests from ServiceNow and sets up the user. 
- If they are in a core domain, it uses the LAN ID. 
- It creates the groups like {KEY}_read, {KEY}_dev, etc. automatically.
- I added a check so only existing space admins can approve new admin requests.

#### 2. Space Creation
Validates the space name and key first (standard rules), then creates everything in one go so we don't have to do it manually in the Confluence UI.

#### 3. Secret Scanner
This is a background service. Confluence sends a webhook when a page changes, and this script scans the text for AWS keys or passwords. If it finds one, it masks it with **** and drops a warning banner at the top of the page.

---

### Security (Vault)
I moved all the passwords out of the code and into HashiCorp Vault. 

**To update the confluence password:**
Run this on the server:
`vault kv put kv/confluence username="admin" password="NEW_PASSWORD"`

The scripts will pick it up automatically next time they run.

---

### Managing the services

I set these up as systemd services so they stay running. 

**To check status:**
`sudo systemctl status confluence-automation`
`sudo systemctl status secret-scanner`

**To restart:**
`sudo systemctl restart confluence-automation`
`sudo systemctl restart secret-scanner`

**To see what's happening (logs):**
`journalctl -u confluence-automation -f`

---

### Files
- ui_server.py: The dashboard and API.
- secret_scanner.py: The masking logic.
- vault_utils.py: Helper to talk to Vault.
- access_automation.py / space_automation.py: The backend work logic.
- setup_webhook.py: Run this once to register the hooks in Confluence.
