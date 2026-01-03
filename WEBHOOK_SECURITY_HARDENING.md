# 🔒 Webhook Security Hardening Guide

Complete step-by-step guide to secure your Confluence webhook services.

---

## 🎯 Security Layers to Implement

```
Layer 1: Environment Variables (Credentials)
Layer 2: API Key Authentication
Layer 3: IP Whitelisting (Firewall)
Layer 4: HTTPS/SSL Encryption
Layer 5: Rate Limiting
Layer 6: Input Validation
Layer 7: Audit Logging
```

---

## 📋 Step 1: Move Credentials to Environment Variables

### Current Issue:
```python
# ❌ INSECURE - Hardcoded in code
CONFLUENCE_USERNAME = "admin"
CONFLUENCE_PASSWORD = "xxxxxxx"
```

### Solution:

**1.1 Create environment file on VM:**

```bash
# Connect to VM via PuTTY
cd /opt/confluence-automation

# Create .env file
sudo nano .env
```

**Add this content:**
```bash
CONFLUENCE_URL=http://57.159.25.203:8090
CONFLUENCE_USERNAME=admin
CONFLUENCE_PASSWORD=xxxxxxx
WEBHOOK_API_KEY=your-super-secret-api-key-here-change-this
ALLOWED_IPS=57.159.25.203,127.0.0.1
```

**1.2 Secure the .env file:**
```bash
# Only owner can read
sudo chmod 600 .env
sudo chown admin:admin .env
```

**1.3 Install python-dotenv:**
```bash
source .venv/bin/activate
pip install python-dotenv
```

**1.4 Update requirements.txt:**
```bash
echo "python-dotenv>=1.0.0" >> requirements.txt
```

**1.5 Update Python files to use environment variables:**

Add to top of `ui_server.py`, `secret_scanner.py`, `access_automation.py`:
```python
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Use environment variables
CONFLUENCE_URL = os.getenv('CONFLUENCE_URL')
CONFLUENCE_USERNAME = os.getenv('CONFLUENCE_USERNAME')
CONFLUENCE_PASSWORD = os.getenv('CONFLUENCE_PASSWORD')
```

---

## 🔑 Step 2: Add API Key Authentication

### 2.1 Update `ui_server.py`:

Add this after imports:
```python
from functools import wraps
from flask import abort

WEBHOOK_API_KEY = os.getenv('WEBHOOK_API_KEY')

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key or api_key != WEBHOOK_API_KEY:
            logger.warning(f"Unauthorized access attempt from {request.remote_addr}")
            abort(401, description="Invalid or missing API key")
        return f(*args, **kwargs)
    return decorated_function
```

Add decorator to protected endpoints:
```python
@app.route('/api/requests', methods=['POST'])
@require_api_key  # Add this line
def create_request():
    # existing code...

@app.route('/api/space-requests', methods=['POST'])
@require_api_key  # Add this line
def create_space_request():
    # existing code...
```

### 2.2 Update `secret_scanner.py`:

Add same authentication:
```python
WEBHOOK_API_KEY = os.getenv('WEBHOOK_API_KEY')

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key or api_key != WEBHOOK_API_KEY:
            logger.warning(f"Unauthorized access from {request.remote_addr}")
            abort(401)
        return f(*args, **kwargs)
    return decorated_function

@app.route('/webhook/page-created', methods=['POST'])
@require_api_key  # Add this
def page_created():
    # existing code...

@app.route('/webhook/page-updated', methods=['POST'])
@require_api_key  # Add this
def page_updated():
    # existing code...
```

### 2.3 Update Confluence webhooks to include API key:

```bash
# Update setup_webhook.py to include API key in headers
# Modify the create_webhook function:
```

```python
webhook_data = {
    "name": f"Secret Scanner - {event_type}",
    "url": f"{SCANNER_URL}{endpoint}",
    "events": [event_type],
    "active": True,
    "sslVerificationRequired": False,
    "configuration": {
        "headers": {
            "X-API-Key": os.getenv('WEBHOOK_API_KEY')
        }
    }
}
```

---

## 🛡️ Step 3: IP Whitelisting with Firewall

### 3.1 Configure UFW (Uncomplicated Firewall):

```bash
# Check firewall status
sudo ufw status

# Enable firewall if not enabled
sudo ufw enable

# Allow SSH (IMPORTANT - don't lock yourself out!)
sudo ufw allow 22/tcp

# Allow Confluence
sudo ufw allow 8090/tcp

# DENY public access to webhook ports
sudo ufw deny 5001/tcp
sudo ufw deny 5002/tcp

# ALLOW only from Confluence server IP
sudo ufw allow from 57.159.25.203 to any port 5001
sudo ufw allow from 57.159.25.203 to any port 5002

# Allow localhost
sudo ufw allow from 127.0.0.1 to any port 5001
sudo ufw allow from 127.0.0.1 to any port 5002

# Check rules
sudo ufw status numbered
```

### 3.2 Add IP validation in code (defense in depth):

Add to `ui_server.py` and `secret_scanner.py`:

```python
ALLOWED_IPS = os.getenv('ALLOWED_IPS', '127.0.0.1').split(',')

@app.before_request
def check_ip_whitelist():
    # Skip for health check
    if request.path == '/health':
        return
    
    client_ip = request.remote_addr
    if client_ip not in ALLOWED_IPS:
        logger.warning(f"Blocked request from unauthorized IP: {client_ip}")
        abort(403, description="Access denied from your IP address")
```

---

## 🔐 Step 4: HTTPS/SSL Encryption

### Option A: Using Nginx Reverse Proxy (Recommended)

**4.1 Install Nginx:**
```bash
sudo apt update
sudo apt install nginx
```

**4.2 Create Nginx configuration:**
```bash
sudo nano /etc/nginx/sites-available/confluence-automation
```

**Add this content:**
```nginx
# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name 57.159.25.203;
    return 301 https://$server_name$request_uri;
}

# HTTPS server for automation UI
server {
    listen 443 ssl;
    server_name 57.159.25.203;

    # SSL certificate (self-signed for now)
    ssl_certificate /etc/nginx/ssl/nginx.crt;
    ssl_certificate_key /etc/nginx/ssl/nginx.key;

    # SSL settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Proxy to automation UI
    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket support
    location /socket.io {
        proxy_pass http://127.0.0.1:5001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}

# HTTPS server for secret scanner
server {
    listen 5003 ssl;
    server_name 57.159.25.203;

    ssl_certificate /etc/nginx/ssl/nginx.crt;
    ssl_certificate_key /etc/nginx/ssl/nginx.key;

    location / {
        proxy_pass http://127.0.0.1:5002;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

**4.3 Generate self-signed SSL certificate:**
```bash
# Create SSL directory
sudo mkdir -p /etc/nginx/ssl

# Generate certificate (valid for 365 days)
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/nginx/ssl/nginx.key \
  -out /etc/nginx/ssl/nginx.crt \
  -subj "/C=IN/ST=State/L=City/O=Organization/CN=57.159.25.203"
```

**4.4 Enable the site:**
```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/confluence-automation /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
```

**4.5 Update firewall:**
```bash
sudo ufw allow 443/tcp
sudo ufw allow 5003/tcp
```

### Option B: Production SSL with Let's Encrypt (If you have a domain)

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate (replace with your domain)
sudo certbot --nginx -d yourdomain.com

# Auto-renewal is configured automatically
```

---

## ⏱️ Step 5: Rate Limiting

### 5.1 Install Flask-Limiter:
```bash
source .venv/bin/activate
pip install Flask-Limiter
echo "Flask-Limiter>=3.5.0" >> requirements.txt
```

### 5.2 Update `ui_server.py`:
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Add after app creation
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# Add to specific endpoints
@app.route('/api/requests', methods=['POST'])
@limiter.limit("10 per minute")  # Max 10 requests per minute
@require_api_key
def create_request():
    # existing code...

@app.route('/api/space-requests', methods=['POST'])
@limiter.limit("5 per minute")  # Max 5 space creations per minute
@require_api_key
def create_space_request():
    # existing code...
```

### 5.3 Update `secret_scanner.py`:
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["1000 per hour"]
)

@app.route('/webhook/page-created', methods=['POST'])
@limiter.limit("100 per minute")
@require_api_key
def page_created():
    # existing code...
```

---

## ✅ Step 6: Input Validation

### 6.1 Install validation library:
```bash
pip install cerberus
echo "cerberus>=1.3.5" >> requirements.txt
```

### 6.2 Add validation to `ui_server.py`:
```python
from cerberus import Validator

# Define schemas
access_request_schema = {
    'lan_id': {'type': 'string', 'minlength': 1, 'maxlength': 50, 'required': True},
    'email': {'type': 'string', 'regex': '^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', 'required': True},
    'full_name': {'type': 'string', 'minlength': 1, 'maxlength': 100, 'required': True},
    'domain': {'type': 'string', 'allowed': ['r1-core', 'r2-core', 'r3-core', 'r4-core', 'r5-core', 'r6-core', 'r7-core', 'other'], 'required': True},
    'space_key': {'type': 'string', 'regex': '^[A-Z]{1,5}$', 'required': True},
    'access': {'type': 'string', 'allowed': ['read', 'dev', 'admin'], 'required': True},
    'manager': {'type': 'string', 'minlength': 1, 'maxlength': 50, 'required': True},
    'requester': {'type': 'string', 'minlength': 1, 'maxlength': 50, 'required': True}
}

space_request_schema = {
    'space_name': {'type': 'string', 'minlength': 1, 'maxlength': 100, 'required': True},
    'space_key': {'type': 'string', 'regex': '^[A-Z]{1,5}$', 'required': True},
    'description': {'type': 'string', 'maxlength': 500},
    'space_admin': {'type': 'string', 'minlength': 1, 'maxlength': 50, 'required': True}
}

@app.route('/api/requests', methods=['POST'])
@limiter.limit("10 per minute")
@require_api_key
def create_request():
    data = request.get_json()
    
    # Validate input
    v = Validator(access_request_schema)
    if not v.validate(data):
        logger.warning(f"Invalid request data: {v.errors}")
        return jsonify({"error": "Invalid input", "details": v.errors}), 400
    
    # Continue with existing code...
```

---

## 📊 Step 7: Enhanced Audit Logging

### 7.1 Update logging configuration:

Add to `ui_server.py` and `secret_scanner.py`:

```python
import logging
from logging.handlers import RotatingFileHandler
import json
from datetime import datetime

# Enhanced logging setup
def setup_security_logging():
    # Create security logger
    security_logger = logging.getLogger('security')
    security_logger.setLevel(logging.INFO)
    
    # File handler with rotation
    handler = RotatingFileHandler(
        '/var/log/confluence-automation/security.log',
        maxBytes=10485760,  # 10MB
        backupCount=10
    )
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    security_logger.addHandler(handler)
    
    return security_logger

security_logger = setup_security_logging()

# Log all requests
@app.before_request
def log_request():
    security_logger.info(json.dumps({
        'event': 'request',
        'timestamp': datetime.utcnow().isoformat(),
        'ip': request.remote_addr,
        'method': request.method,
        'path': request.path,
        'user_agent': request.headers.get('User-Agent'),
        'api_key_present': 'X-API-Key' in request.headers
    }))

# Log authentication failures
def log_auth_failure(reason, ip):
    security_logger.warning(json.dumps({
        'event': 'auth_failure',
        'timestamp': datetime.utcnow().isoformat(),
        'reason': reason,
        'ip': ip
    }))

# Log successful operations
def log_operation(operation, user, details):
    security_logger.info(json.dumps({
        'event': 'operation',
        'timestamp': datetime.utcnow().isoformat(),
        'operation': operation,
        'user': user,
        'details': details
    }))
```

### 7.2 Create log directory:
```bash
sudo mkdir -p /var/log/confluence-automation
sudo chown admin:admin /var/log/confluence-automation
```

---

## 🔄 Step 8: Update Services

### 8.1 Update service files to load .env:

Edit `/etc/systemd/system/confluence-automation.service`:
```ini
[Service]
Type=simple
User=admin
WorkingDirectory=/opt/confluence-automation
Environment="PATH=/opt/confluence-automation/.venv/bin"
EnvironmentFile=/opt/confluence-automation/.env
ExecStart=/opt/confluence-automation/.venv/bin/python /opt/confluence-automation/ui_server.py
```

Edit `/etc/systemd/system/secret-scanner.service`:
```ini
[Service]
Type=simple
User=admin
WorkingDirectory=/opt/confluence-automation
Environment="PATH=/opt/confluence-automation/.venv/bin"
EnvironmentFile=/opt/confluence-automation/.env
ExecStart=/opt/confluence-automation/.venv/bin/python /opt/confluence-automation/secret_scanner.py
```

### 8.2 Reload and restart services:
```bash
sudo systemctl daemon-reload
sudo systemctl restart confluence-automation
sudo systemctl restart secret-scanner
```

---

## ✅ Verification Checklist

### Test Security Implementation:

```bash
# 1. Test without API key (should fail)
curl -X POST http://57.159.25.203:5001/api/requests \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'
# Expected: 401 Unauthorized

# 2. Test with API key (should work)
curl -X POST http://57.159.25.203:5001/api/requests \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-super-secret-api-key-here-change-this" \
  -d '{"lan_id": "test", "email": "test@example.com", ...}'
# Expected: 200 OK or validation error

# 3. Test from unauthorized IP (should fail)
# Try from different machine
# Expected: 403 Forbidden

# 4. Test HTTPS (if configured)
curl -k https://57.159.25.203/health
# Expected: 200 OK

# 5. Test rate limiting
# Make 11 requests in 1 minute
for i in {1..11}; do
  curl -X POST http://57.159.25.203:5001/api/requests \
    -H "X-API-Key: your-key" \
    -H "Content-Type: application/json" \
    -d '{"test": "data"}'
done
# Expected: 11th request should fail with 429 Too Many Requests

# 6. Check security logs
tail -f /var/log/confluence-automation/security.log
```

---

## 📋 Complete Security Checklist

- [ ] ✅ Credentials moved to environment variables
- [ ] ✅ API key authentication implemented
- [ ] ✅ Firewall rules configured (UFW)
- [ ] ✅ IP whitelisting enabled
- [ ] ✅ HTTPS/SSL configured (Nginx)
- [ ] ✅ Rate limiting implemented
- [ ] ✅ Input validation added
- [ ] ✅ Enhanced audit logging configured
- [ ] ✅ Services updated and restarted
- [ ] ✅ Security tests passed

---

## 🚨 Security Maintenance

### Regular Tasks:

**Daily:**
- Monitor security logs: `tail -f /var/log/confluence-automation/security.log`

**Weekly:**
- Review failed authentication attempts
- Check for unusual IP addresses
- Verify rate limiting is working

**Monthly:**
- Rotate API keys
- Update SSL certificates (if needed)
- Review and update firewall rules
- Update dependencies: `pip install --upgrade -r requirements.txt`

**Quarterly:**
- Security audit
- Penetration testing
- Review access logs

---

## 📊 Security Levels Achieved

| Security Measure | Before | After |
|-----------------|--------|-------|
| Credential Security | 🔴 Hardcoded | 🟢 Environment vars |
| Authentication | 🔴 None | 🟢 API key |
| Network Security | 🔴 Open ports | 🟢 Firewall + IP whitelist |
| Encryption | 🔴 HTTP | 🟢 HTTPS/SSL |
| Rate Limiting | 🔴 None | 🟢 Implemented |
| Input Validation | 🔴 None | 🟢 Schema validation |
| Audit Logging | 🟡 Basic | 🟢 Enhanced |
| **Overall Risk** | 🔴 **HIGH** | 🟢 **LOW-MEDIUM** |

---

## 🎯 Summary

After implementing all steps, your webhook security will have:

✅ **Authentication** - API key required  
✅ **Authorization** - IP whitelisting  
✅ **Encryption** - HTTPS/SSL  
✅ **Rate Limiting** - DDoS protection  
✅ **Input Validation** - Injection prevention  
✅ **Audit Logging** - Compliance & monitoring  
✅ **Credential Security** - No hardcoded secrets  

**Your webhooks will be production-ready and secure!** 🔒🚀
