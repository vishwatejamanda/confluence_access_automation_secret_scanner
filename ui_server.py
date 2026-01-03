from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import logging
from datetime import datetime
import json
import os
from threading import Lock
from access_automation import AccessManager
from space_automation import SpaceCreationManager
from vault_utils import VaultManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

URL = "http://57.159.25.203:8090"
DB_FILE = "/tmp/confluence_requests.json"
lock = Lock()

try:
    vault = VaultManager()
    USER, PW = vault.get_confluence_credentials()
except Exception as e:
    logger.critical(f"Vault error: {e}")
    raise RuntimeError("Vault required")

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    return []

def save_db(data):
    with open(DB_FILE, 'w') as f:
        json.dump(data, f, indent=2)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/requests', methods=['GET'])
def get_reqs():
    return jsonify(load_db())

@app.route('/api/requests', methods=['POST'])
def create_req():
    data = request.json
    fields = ['lan_id', 'email', 'domain', 'manager', 'requester', 'full_name', 'space_key', 'access']
    if any(f not in data for f in fields):
        return jsonify({"error": "Missing fields"}), 400
    
    with lock:
        db = load_db()
        next_id = max([r.get('id', 0) for r in db], default=0) + 1
        req = {
            "id": next_id, "status": "pending", 
            "created_at": datetime.now().isoformat(),
            "data": data, "result": None
        }
        db.append(req)
        save_db(db)
    
    socketio.emit('request_created', req)
    socketio.start_background_task(run_access_task, next_id)
    return jsonify(req), 201

def run_access_task(rid):
    update_status(rid, 'processing')
    db = load_db()
    req = next((r for r in db if r['id'] == rid), None)
    if not req: return
    
    mgr = AccessManager(URL, USER, PW)
    res = mgr.process_request(req['data'])
    
    if res.get('status') == 'success':
        update_status(rid, 'completed', result=res)
    else:
        update_status(rid, 'failed', error=res.get('message'))

def update_status(rid, status, error=None, result=None):
    with lock:
        db = load_db()
        req = next((r for r in db if r['id'] == rid), None)
        if req:
            req['status'] = status
            req['updated_at'] = datetime.now().isoformat()
            if error: req['error'] = error
            if result: req['result'] = result
            save_db(db)
            socketio.emit('request_updated', req)

@app.route('/api/stats', methods=['GET'])
def stats():
    db = load_db()
    return jsonify({
        "total": len(db),
        "pending": len([r for r in db if r['status'] == 'pending']),
        "processing": len([r for r in db if r['status'] == 'processing']),
        "completed": len([r for r in db if r['status'] == 'completed']),
        "failed": len([r for r in db if r['status'] == 'failed'])
    })

@app.route('/api/space-requests', methods=['POST'])
def space_req():
    data = request.json
    if not all(k in data for k in ['space_name', 'space_key', 'space_admin']):
        return jsonify({"error": "Missing fields"}), 400
    
    with lock:
        db = load_db()
        next_id = max([r.get('id', 0) for r in db], default=0) + 1
        req = {
            "id": next_id, "type": "space_creation", "status": "pending",
            "created_at": datetime.now().isoformat(), "data": data
        }
        db.append(req)
        save_db(db)
    
    socketio.emit('request_created', req)
    socketio.start_background_task(run_space_task, next_id)
    return jsonify(req), 201

def run_space_task(rid):
    update_status(rid, 'processing')
    db = load_db()
    req = next((r for r in db if r['id'] == rid), None)
    if not req: return
    
    mgr = SpaceCreationManager(URL, USER, PW)
    res = mgr.process_request(req['data'])
    
    with lock:
        db = load_db()
        r = next((i for i in db if i['id'] == rid), None)
        if r:
            r['comments'] = res.get('comments', [])
            r['status'] = 'completed' if res.get('status') == 'success' else 'failed'
            if res.get('status') != 'success': r['error'] = res.get('error', 'Failed')
            r['result'] = res
            save_db(db)
            socketio.emit('request_updated', r)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5001, debug=False, allow_unsafe_werkzeug=True)
