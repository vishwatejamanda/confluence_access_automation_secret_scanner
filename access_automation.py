from atlassian import Confluence
import logging
import requests

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AccessManager:
    def __init__(self, url, username, password):
        self.confluence = Confluence(
            url=url,
            username=username,
            password=password
        )

    def get_username(self, lan_id, email, domain):
        # r1-core uses LAN ID, others use email
        return lan_id if domain == 'r1-core' else email

    def ensure_user_exists(self, email, full_name, username, password):
        try:
            user = self.confluence.get_user_details_by_username(username)
            logger.info(f"User {username} exists")
        except Exception:
            logger.info(f"Creating user {username}...")
            try:
                endpoint = f"{self.confluence.url}/rest/api/admin/user"
                payload = {
                    "userName": username,
                    "fullName": full_name,
                    "email": email,
                    "password": password,
                    "notifyViaEmail": False
                }
                
                resp = requests.post(
                    endpoint,
                    json=payload,
                    auth=(self.confluence.username, self.confluence.password),
                    headers={"Accept": "application/json", "Content-Type": "application/json"}
                )
                
                if resp.status_code in [200, 201]:
                    user = self.confluence.get_user_details_by_username(username)
                else:
                    logger.error(f"User creation failed: {resp.status_code}")
                    return None
            except Exception as e:
                logger.error(f"Creation error: {e}")
                return None

        # Ensure license
        if not self.is_user_in_group(username, "confluence-users"):
            try:
                self.confluence.add_user_to_group(username, "confluence-users")
            except Exception as e:
                logger.error(f"License assignment failed: {e}")
        
        return user

    def is_user_in_group(self, username, group_name):
        try:
            members = self.confluence.get_group_members(group_name)
            return any(m.get('username') == username for m in members)
        except Exception:
            return False

    def is_space_admin(self, space_key, username):
        try:
            details = self.confluence.get_user_details_by_username(username)
            ukey = details.get('userKey')
            perms = self.confluence.get_all_space_permissions(space_key)
            for p in perms:
                if (p.get('operation', {}).get('operationKey') == 'administer' and 
                    p.get('subject', {}).get('userKey') == ukey):
                    return True
        except Exception:
            pass
        return False

    def ensure_space_groups_exist(self, space_key):
        for gtype in ['read', 'dev', 'admin']:
            name = f"{space_key}_{gtype}"
            try:
                self.confluence.create_group(name)
            except Exception:
                pass

    def process_request(self, data):
        lan_id = data.get('lan_id')
        email = data.get('email')
        domain = data.get('domain')
        full_name = data.get('full_name')
        mgr = data.get('manager')
        req = data.get('requester')
        key = data.get('space_key')
        access = data.get('access', 'read')

        username = self.get_username(lan_id, email, domain)
        user_info = self.ensure_user_exists(email, full_name, username, email)
        
        if not user_info:
             return {"status": "error", "message": "User setup failed"}

        self.ensure_space_groups_exist(key)

        if access == 'admin':
            if not (self.is_space_admin(key, mgr) or self.is_space_admin(key, req)):
                logger.warning(f"Admin denied for {username}. Downgrading to dev.")
                access = 'dev'

        group = f"{key}_{access}"
        try:
            if not self.is_user_in_group(username, group):
                self.confluence.add_user_to_group(username, group)
            
            return {
                "status": "success", 
                "username": username, 
                "access_granted": access,
                "group": group
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    from vault_utils import VaultManager
    import sys
    
    try:
        vault = VaultManager()
        u, p = vault.get_confluence_credentials()
        url = "http://57.159.25.203:8090"
    except Exception:
        print("Vault error")
        sys.exit(1)

    mgr = AccessManager(url, u, p)
    test_data = {
        "lan_id": "testuser",
        "email": "test@gmail.com",
        "manager": "admin",
        "requester": "admin",
        "full_name": "Test User",
        "space_key": "VIS",
        "access": "admin",
        "domain": "r1-core"
    }
    print(mgr.process_request(test_data))
