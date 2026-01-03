from atlassian import Confluence
import logging
import requests
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SpaceCreationManager:
    def __init__(self, url, username, password):
        self.confluence = Confluence(url=url, username=username, password=password)
        self.url = url
        self.username = username
        self.password = password
    
    def validate_name(self, name):
        if not name: return False, "Name is required"
        if name[0].isdigit(): return False, "Name can't start with a number"
        return True, None
    
    def validate_key(self, key):
        if not key: return False, "Key is required"
        if len(key) > 5: return False, "Key max 5 chars"
        if not key.isupper() or not key.isalpha(): return False, "Key must be uppercase letters only"
        return True, None
    
    def has_license(self, username):
        try:
            members = self.confluence.get_group_members("confluence-users")
            return any(m.get('username') == username for m in members)
        except Exception:
            return False
    
    def user_exists(self, username):
        try:
            self.confluence.get_user_details_by_username(username)
            return True
        except:
            return False
    
    def create_space(self, key, name, desc):
        endpoint = f"{self.url}/rest/api/space"
        payload = {
            "key": key,
            "name": name,
            "description": {"plain": {"value": desc, "representation": "plain"}},
            "type": "global"
        }
        try:
            r = requests.post(
                endpoint, json=payload, 
                auth=(self.username, self.password),
                headers={"Accept": "application/json", "Content-Type": "application/json"}
            )
            if r.status_code in [200, 201]:
                return True, r.json()
            return False, r.text
        except Exception as e:
            return False, str(e)
    
    def setup_groups(self, key):
        for gtype in ['read', 'dev', 'admin']:
            name = f"{key}_{gtype}"
            try:
                self.confluence.create_group(name)
                self.assign_perms(key, name, gtype)
            except Exception:
                pass

    def assign_perms(self, key, group, gtype):
        perms = []
        if gtype == 'read':
            perms = [{"targetType": "space", "operationKey": "read"}]
        elif gtype == 'dev':
            objs = ["page", "blogpost", "comment", "attachment"]
            ops = ["create", "delete", "read"] #Simplified
            perms = [{"targetType": "space", "operationKey": "read"}]
            for t in ["page", "blogpost", "comment", "attachment"]:
                perms.append({"targetType": t, "operationKey": "create"})
                perms.append({"targetType": t, "operationKey": "delete"})
        elif gtype == 'admin':
            perms = [{"targetType": "space", "operationKey": "administer"}]

        try:
            endpoint = f"{self.url}/rest/api/space/{key}/permissions/group/{group}/grant"
            requests.put(
                endpoint, json=perms, 
                auth=(self.username, self.password),
                headers={"Accept": "application/json", "Content-Type": "application/json"}
            )
        except:
            pass

    def process_request(self, data):
        name = data.get('space_name')
        key = data.get('space_key')
        desc = data.get('description', '')
        admin = data.get('space_admin')
        
        comments = []
        issues = []
        
        v_name, e_name = self.validate_name(name)
        if not v_name: issues.append(e_name); comments.append(f"❌ {e_name}")
        
        v_key, e_key = self.validate_key(key)
        if not v_key: issues.append(e_key); comments.append(f"❌ {e_key}")
        
        if not self.user_exists(admin):
            issues.append("Admin doesn't exist"); comments.append(f"⚠️ User {admin} not found")
        elif not self.has_license(admin):
            issues.append("No license"); comments.append(f"⚠️ User {admin} has no license")
        
        if issues:
            return {"status": "work_in_progress", "comments": comments, "issues": issues}
        
        success, res = self.create_space(key, name, desc)
        if not success:
            return {"status": "failed", "comments": [f"❌ Creation failed: {res}"]}
        
        url = f"{self.url}/display/{key}"
        self.setup_groups(key)
        
        time.sleep(1) # Wait for sync
        
        try:
            self.confluence.add_user_to_group(admin, f"{key}_admin")
            comments.append(f"✅ Space {key} created. {admin} added as admin.")
        except Exception as e:
            comments.append(f"⚠️ Could not add {admin} to admin group: {e}")
            
        return {
            "status": "success",
            "comments": comments,
            "space_url": url,
            "space_key": key
        }

if __name__ == "__main__":
    from vault_utils import VaultManager
    import sys
    try:
        vault = VaultManager()
        u, p = vault.get_confluence_credentials()
        mgr = SpaceCreationManager("http://57.159.25.203:8090", u, p)
        print(mgr.process_request({"space_name": "Test", "space_key": "TS", "space_admin": "admin"}))
    except Exception as e:
        print(f"Error: {e}")
