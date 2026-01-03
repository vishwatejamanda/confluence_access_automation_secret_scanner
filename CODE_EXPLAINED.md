# How the code works

Here is a quick breakdown of what each file in the project actually does. 

### 1. ui_server.py
This is the main entry point for the dashboard. It's a Flask app that handles the web UI and the API. 
- I used **SocketIO** so when a request comes in from ServiceNow, the dashboard updates in real-time without you having to refresh.
- It saves everything to a local JSON file (`/tmp/confluence_requests.json`) so we have a history of what happened.
- It also triggers the background tasks for creating users or spaces so the API response stays fast.

### 2. secret_scanner.py
This is the security guard. It listens for webhooks from Confluence whenever a page is "created" or "updated".
- It uses a bunch of **Regex** patterns to find things like AWS keys, GitHub tokens, or passwords.
- If it finds something, it immediately talks back to Confluence, masks the secret with `****`, and bumps the page version.
- It's running on port 5002.

### 3. access_automation.py
This file handles the logic for Confluence users and groups.
- It checks if a user exists based on their email or LAN ID.
- It auto-creates users via the Admin REST API if they are missing.
- It manages the group structure (`{KEY}_read`, `{KEY}_dev`, `{KEY}_admin`).
- It has the logic to fallback to `dev` access if an unauthorized person tries to request `admin` permissions.

### 4. space_automation.py
This is for the "Create Space" workflow.
- It validates the input first (making sure keys are uppercase and names don't start with numbers).
- It creates the space and then runs its own internal logic to set up the default permissions for the read/dev/admin groups.
- It also makes sure the person being assigned as the "Space Admin" actually has a license first.

### 5. vault_utils.py
I wrote this to handle all the credentials. 
- It connects to **HashiCorp Vault** using the root token.
- It fetches the Confluence admin username and password from the `kv/confluence` path.
- This is why none of the other scripts have hardcoded passwords in them anymore.

### 6. setup_webhook.py
You only need to run this once. 
- It tells Confluence: "Hey, whenever a page changes, send a notification to our secret_scanner.py at this URL."
- It registers the `page_created` and `page_updated` events.
