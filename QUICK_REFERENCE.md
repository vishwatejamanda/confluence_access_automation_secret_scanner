# Flask Webhook Server - Quick Reference

## 🚀 Server Status
✅ **Running on**: http://localhost:5000 (and http://192.168.1.10:5000)
✅ **Logs**: `/tmp/confluence_webhook.log`

---

## 📡 Available Endpoints

### 1️⃣ Health Check
```bash
curl http://localhost:5000/health
```
**Response**: `{"status": "healthy", "timestamp": "...", "service": "Confluence Automation Webhook"}`

---

### 2️⃣ Space Creation (Auto-create groups)
```bash
curl -X POST http://localhost:5000/webhook/space-created \
  -H "Content-Type: application/json" \
  -d '{"space_key": "NEWSPACE"}'
```

**What it does**:
- Creates `NEWSPACE_read` group
- Creates `NEWSPACE_dev` group  
- Creates `NEWSPACE_admin` group

---

### 3️⃣ Access Request (Single User)
```bash
curl -X POST http://localhost:5000/webhook/access-request \
  -H "Content-Type: application/json" \
  -d '{
    "lan_id": "user123",
    "email": "user@example.com",
    "domain": "r1-core",
    "manager": "admin",
    "requester": "admin",
    "full_name": "John Doe",
    "space_key": "VIS",
    "access": "admin"
  }'
```

**What it does**:
1. ✅ Creates user if doesn't exist (username = LAN ID for r1-core to r7-core)
2. ✅ Assigns Confluence license (adds to confluence-users)
3. ✅ Creates space groups if needed (VIS_read, VIS_dev, VIS_admin)
4. ✅ Validates admin access (checks if manager/requester is space admin)
5. ✅ Adds user to appropriate group

---

### 4️⃣ Batch Access Request
```bash
curl -X POST http://localhost:5000/webhook/batch-access-request \
  -H "Content-Type: application/json" \
  -d '{
    "requests": [
      {
        "lan_id": "user1",
        "email": "user1@example.com",
        "domain": "r1-core",
        "manager": "admin",
        "requester": "admin",
        "full_name": "User One",
        "space_key": "VIS",
        "access": "read"
      },
      {
        "lan_id": "user2",
        "email": "user2@example.com",
        "domain": "other",
        "manager": "admin",
        "requester": "admin",
        "full_name": "User Two",
        "space_key": "VIS",
        "access": "dev"
      }
    ]
  }'
```

---

## 🔧 How to Use with ServiceNow

### Step 1: Create Outbound REST Message in ServiceNow
1. Go to **System Web Services** → **Outbound** → **REST Message**
2. Name: `Confluence Access Automation`
3. Endpoint: `http://YOUR_SERVER_IP:5000/webhook/access-request`
4. HTTP Method: `POST`
5. HTTP Headers: `Content-Type: application/json`

### Step 2: Create Business Rule
Trigger: When access request is submitted

```javascript
(function executeRule(current, previous) {
    var r = new sn_ws.RESTMessageV2('Confluence Access Automation', 'Default POST');
    
    var payload = {
        lan_id: current.getValue('lan_id'),
        email: current.getValue('email'),
        domain: current.getValue('domain'),
        manager: current.getValue('manager'),
        requester: current.getValue('requester'),
        full_name: current.getValue('full_name'),
        space_key: current.getValue('space_key'),
        access: current.getValue('access_level')
    };
    
    r.setRequestBody(JSON.stringify(payload));
    var response = r.execute();
    
    if (response.getStatusCode() == 200) {
        current.work_notes = 'Access granted: ' + response.getBody();
        current.state = 'Completed';
    } else {
        current.work_notes = 'Failed: ' + response.getBody();
        current.state = 'Failed';
    }
    current.update();
})(current, previous);
```

---

## 🎯 Business Logic

### Username Generation
- **r1-core to r7-core domains**: Username = LAN ID
- **All other domains**: Username = Email

### Password
- Always set to **Email address**

### Access Level Validation
| Requested | Manager/Requester is Space Admin? | Granted |
|-----------|-----------------------------------|---------|
| read      | N/A                               | read    |
| dev       | N/A                               | dev     |
| admin     | ✅ Yes                            | admin   |
| admin     | ❌ No                             | dev     |

### Space Groups Convention
For space key `VIS`:
- `VIS_read` - Read access
- `VIS_dev` - Developer access (read + create + edit)
- `VIS_admin` - Admin access (full control)

---

## 📊 Testing

Run the test script:
```bash
./test_webhooks.sh
```

Or test individual endpoints:
```bash
# Health check
curl http://localhost:5000/health

# Test access request
curl -X POST http://localhost:5000/webhook/access-request \
  -H "Content-Type: application/json" \
  -d '{
    "lan_id": "xxxxxxxtejatest1",
    "email": "xxxxxxx@gmail.com",
    "domain": "r1-core",
    "manager": "admin",
    "requester": "admin",
    "full_name": "xxxxxxx Teja",
    "space_key": "VIS",
    "access": "dev"
  }'
```

---

## 🔍 Monitoring

### View Logs
```bash
# Real-time logs
tail -f /tmp/confluence_webhook.log

# Last 100 lines
tail -n 100 /tmp/confluence_webhook.log

# Search for errors
grep ERROR /tmp/confluence_webhook.log
```

### Check Server Status
```bash
# Check if running
ps aux | grep webhook_server

# Check port
sudo lsof -i :5000

# Test health
curl http://localhost:5000/health
```

---

## 🛑 Stop/Start Server

### Stop
```bash
# Find process
ps aux | grep webhook_server

# Kill process
kill <PID>

# Or use Ctrl+C in the terminal where it's running
```

### Start
```bash
cd /home/xxxxxxxtejamanda/CascadeProjects/confluencetesting
source .venv/bin/activate
python webhook_server.py
```

### Start in Background
```bash
nohup python webhook_server.py > /tmp/webhook_server.out 2>&1 &
```

---

## 🔐 Security (TODO for Production)

1. **Add API Key Authentication**
   - Require `X-API-Key` header
   
2. **Use HTTPS**
   - Set up nginx reverse proxy with SSL certificate
   
3. **Rate Limiting**
   - Install flask-limiter
   - Limit to 100 requests per hour per IP

4. **Firewall**
   - Only allow ServiceNow IP addresses
   ```bash
   sudo ufw allow from SERVICENOW_IP to any port 5000
   ```

---

## 📞 Support

**Documentation**:
- `README.md` - Project overview
- `WEBHOOK_GUIDE.md` - Detailed webhook documentation
- `TRIGGERING_GUIDE.md` - Alternative triggering methods

**Logs**: `/tmp/confluence_webhook.log`

**Test Script**: `./test_webhooks.sh`
