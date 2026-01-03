# 🚀 Step-by-Step Deployment to VM (57.159.25.203)

## Server Details
- **VM IP**: 57.159.25.203
- **Confluence**: http://57.159.25.203:8090/
- **Automation UI**: Will run on http://57.159.25.203:5001/

---

## 📋 Step 1: Create Deployment Package (On Your Local Machine)

```bash
cd /home/xxxxxxxtejamanda/CascadeProjects/confluencetesting

# Create a clean package
tar -czf confluence-automation.tar.gz \
  ui_server.py \
  access_automation.py \
  space_automation.py \
  requirements.txt \
  start_ui.sh \
  templates/ \
  static/ \
  README.md \
  COMPLETE_SOLUTION.md

# Verify the package
tar -tzf confluence-automation.tar.gz
```

---

## 📤 Step 2: Transfer Files to VM

### **Option A: Using SCP (Recommended)**

```bash
# Transfer the package
scp confluence-automation.tar.gz admin@57.159.25.203:/home/admin/

# If you need to specify SSH key:
scp -i /path/to/your/key.pem confluence-automation.tar.gz admin@57.159.25.203:/home/admin/
```

### **Option B: Using WinSCP (Windows)**

1. Open WinSCP
2. Connect to: `57.159.25.203`
3. Username: `admin` (or your username)
4. Upload `confluence-automation.tar.gz` to `/home/admin/`

---

## 🔧 Step 3: Connect via PuTTY

1. **Open PuTTY**
2. **Host Name**: `57.159.25.203`
3. **Port**: `22`
4. **Click**: "Open"
5. **Login** with your credentials

---

## 📦 Step 4: Setup on VM (Run these commands in PuTTY)

### **4.1 Extract Files**

```bash
# Navigate to home directory
cd /home/admin

# Create application directory
sudo mkdir -p /opt/confluence-automation
sudo chown $USER:$USER /opt/confluence-automation

# Extract files
tar -xzf confluence-automation.tar.gz -C /opt/confluence-automation

# Go to application directory
cd /opt/confluence-automation
ls -la
```

### **4.2 Install Python Dependencies**

```bash
# Check if Python 3 is installed
python3 --version

# If not installed:
sudo apt update
sudo apt install -y python3 python3-pip python3-venv

# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### **4.3 Update Configuration**

```bash
# Edit ui_server.py to update credentials if needed
nano ui_server.py
```

**Update these lines (around line 25-27):**
```python
CONFLUENCE_URL = "http://57.159.25.203:8090"
CONFLUENCE_USERNAME = "admin"
CONFLUENCE_PASSWORD = "xxxxxxx"
```

Press `Ctrl+X`, then `Y`, then `Enter` to save.

---

## 🚀 Step 5: Test Run

```bash
# Make sure you're in the right directory
cd /opt/confluence-automation

# Activate virtual environment
source .venv/bin/activate

# Run the server
python ui_server.py
```

**You should see:**
```
Starting Confluence Automation UI Server...
Confluence URL: http://57.159.25.203:8090
Server will be available at: http://0.0.0.0:5001
 * Running on http://127.0.0.1:5001
 * Running on http://57.159.25.203:5001
```

**Test it:** Open browser and go to `http://57.159.25.203:5001`

Press `Ctrl+C` to stop the server.

---

## 🔄 Step 6: Setup as System Service (Run in Background)

### **6.1 Create Service File**

```bash
sudo nano /etc/systemd/system/confluence-automation.service
```

**Paste this content:**
```ini
[Unit]
Description=Confluence Automation Service
After=network.target

[Service]
Type=simple
User=admin
WorkingDirectory=/opt/confluence-automation
Environment="PATH=/opt/confluence-automation/.venv/bin"
ExecStart=/opt/confluence-automation/.venv/bin/python /opt/confluence-automation/ui_server.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Press `Ctrl+X`, then `Y`, then `Enter` to save.

### **6.2 Enable and Start Service**

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable confluence-automation

# Start the service
sudo systemctl start confluence-automation

# Check status
sudo systemctl status confluence-automation
```

**You should see:** `Active: active (running)`

---

## 🔥 Step 7: Configure Firewall

```bash
# Check if firewall is active
sudo ufw status

# If active, allow port 5001
sudo ufw allow 5001/tcp

# Check again
sudo ufw status
```

---

## ✅ Step 8: Verify Deployment

### **8.1 Check Service Status**

```bash
sudo systemctl status confluence-automation
```

### **8.2 View Logs**

```bash
# View live logs
sudo journalctl -u confluence-automation -f

# View last 50 lines
sudo journalctl -u confluence-automation -n 50
```

### **8.3 Test the Application**

Open browser and navigate to:
```
http://57.159.25.203:5001
```

You should see the Confluence Automation Dashboard!

---

## 🎯 Common Commands

### **Start Service**
```bash
sudo systemctl start confluence-automation
```

### **Stop Service**
```bash
sudo systemctl stop confluence-automation
```

### **Restart Service**
```bash
sudo systemctl restart confluence-automation
```

### **View Logs**
```bash
sudo journalctl -u confluence-automation -f
```

### **Check Status**
```bash
sudo systemctl status confluence-automation
```

---

## 🔧 Troubleshooting

### **If service fails to start:**

1. **Check logs:**
   ```bash
   sudo journalctl -u confluence-automation -n 100
   ```

2. **Check if port is already in use:**
   ```bash
   sudo netstat -tulpn | grep 5001
   ```

3. **Test manually:**
   ```bash
   cd /opt/confluence-automation
   source .venv/bin/activate
   python ui_server.py
   ```

### **If can't access from browser:**

1. **Check firewall:**
   ```bash
   sudo ufw status
   sudo ufw allow 5001/tcp
   ```

2. **Check if service is running:**
   ```bash
   sudo systemctl status confluence-automation
   ```

3. **Check VM network security group** (if on Azure/cloud)

---

## 📊 Access Points After Deployment

- **Confluence**: http://57.159.25.203:8090/
- **Automation Dashboard**: http://57.159.25.203:5001/
- **API Endpoint (Access)**: http://57.159.25.203:5001/api/requests
- **API Endpoint (Space)**: http://57.159.25.203:5001/api/space-requests

---

## 🎉 You're Done!

Your Confluence Automation is now deployed and running on the VM!

**Next Steps:**
1. Test creating an access request
2. Test creating a space
3. Integrate with ServiceNow
4. Set up monitoring

---

## 📝 Quick Reference

**Service Management:**
```bash
sudo systemctl start confluence-automation    # Start
sudo systemctl stop confluence-automation     # Stop
sudo systemctl restart confluence-automation  # Restart
sudo systemctl status confluence-automation   # Status
```

**Logs:**
```bash
sudo journalctl -u confluence-automation -f   # Live logs
sudo journalctl -u confluence-automation -n 50 # Last 50 lines
```

**Application Directory:**
```bash
cd /opt/confluence-automation
```

**Update Code:**
```bash
cd /opt/confluence-automation
# Upload new files via SCP/WinSCP
sudo systemctl restart confluence-automation
```
