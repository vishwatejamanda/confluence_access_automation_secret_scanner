# Secret Management & Secure Storage Possibilities

This document outlines options for moving away from plain-text passwords on the server.

## 1. System-Level Environment Variables
Instead of using a `.env` file, secrets are set in the operating system's environment.
*   **Implementation:** Set in `/etc/environment` or within the `[Service]` block of a systemd `.service` file.
*   **Security:** Decent; prevents accidental commits to Git, but root users can still see them.

## 2. Systemd LoadCredential (Linux Native)
Modern systemd versions allow passing credentials securely.
*   **Implementation:** `LoadCredential=confluence_pass:/etc/confluence/pass.txt` in the service file.
*   **Security:** Higher; the secret is only available to the running process via a specific file descriptor.

## 3. OS Keyring (Python `keyring` library)
Uses the system's native secure password manager (Windows Credential Manager, macOS Keychain, Linux Secret Service).
*   **Implementation:** `import keyring; pass = keyring.get_password("confluence", "admin")`.
*   **Security:** High; secrets are managed by the OS and often encrypted with the user's login.

## 4. CyberArk (Enterprise PAM)
The industry leader for Privileged Access Management.
*   **Implementation:** Use CyberArk **Application Access Manager (AAM)**. The script makes a secure call to the CyberArk Vault to retrieve credentials at runtime.
*   **Security:** Extremely High; includes automatic password rotation and full enterprise auditing.

## 5. HashiCorp Vault
A dedicated enterprise secret management tool.
*   **Implementation:** App requests secrets via REST API with a temporary token.
*   **Features:** Secret rotation, dynamic secrets (passwords that expire), audit logs.
*   **Security:** Very High; the industry gold standard for DevOps.

## 6. Cloud Vaults (Identity-Based Access)
If the VM is in AWS, Azure, or GCP, use their native Secret Managers.
*   **Implementation:** The VM is assigned an IAM role. The Python code uses a SDK (boto3, etc.) to fetch secrets.
*   **Security:** Very High; **No credentials** are ever stored on the VM. Access is granted based on the "Identity" of the server itself.

## 7. SOPS (Secrets Operations)
Encrypts specific values within a YAML or JSON file using AWS KMS, GCP KMS, Azure Key Vault, or PGP.
*   **Implementation:** You commit `secrets.enc.yaml` to your repo. It remains encrypted until accessed by a system with the correct key.

---

## Recommendation Path
1. **Short Term:** Move from `.env` to restricted Systemd environment variables or the `keyring` library.
2. **Long Term:** Integrate with a Cloud Secret Manager (AWS/Azure) or HashiCorp Vault.
