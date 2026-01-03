import hvac
import os

class VaultManager:
    def __init__(self):
        self.url = os.getenv('VAULT_ADDR', 'http://127.0.0.1:8200')
        self.token = os.getenv('VAULT_TOKEN', 'my-root-token')
        self.client = hvac.Client(url=self.url, token=self.token)

    def get_confluence_credentials(self):
        try:
            res = self.client.secrets.kv.v2.read_secret_version(mount_point='kv', path='confluence')
            data = res['data']['data']
            return data['username'], data['password']
        except Exception as e:
            raise RuntimeError(f"Vault failed: {e}")

if __name__ == "__main__":
    v = VaultManager()
    u, p = v.get_confluence_credentials()
    print(f"Connected as: {u}")
