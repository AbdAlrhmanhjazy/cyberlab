from flask import Flask, render_template, request, jsonify
import sqlite3
import socket
import os

app = Flask(__name__)
DB_NAME = "cyberlab.db"

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    if not os.path.exists(DB_NAME):
        with get_db() as conn:
            with open("schema.sql", "r") as f:
                conn.executescript(f.read())

@app.route('/')
def dashboard():
    return render_template('index.html')

@app.route('/api/targets', methods=['POST'])
def add_target():
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO targets (target_name, ip_or_domain) VALUES (?, ?)",
        (data['name'], data['host'])
    )
    conn.commit()
    return jsonify({"status": "success", "target_id": cursor.lastrowid})

@app.route('/api/scan/start', methods=['POST'])
def start_scan():
    data = request.json
    target_id = data.get('target_id')
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT ip_or_domain FROM targets WHERE id = ?", (target_id,))
    target = cursor.fetchone()
    if not target:
        return jsonify({"error": "Target not found"}), 404

    cursor.execute("INSERT INTO scans (target_id, status) VALUES (?, 'COMPLETED')", (target_id,))
    scan_id = cursor.lastrowid

    host = target['ip_or_domain']
    common_ports = [(80, 'HTTP'), (443, 'HTTPS'), (22, 'SSH'), (21, 'FTP')]
    
    for port, service in common_ports:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.5)
        result = s.connect_ex((host, port))
        if result == 0:
            severity = 'HIGH' if port == 21 else 'LOW'
            cursor.execute("""
                INSERT INTO findings (scan_id, service, port, severity, description, remediation)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (scan_id, service, port, severity, 
                  f"Service {service} is exposed on port {port}.", 
                  "Restrict access via firewall if not needed."))
        s.close()

    conn.commit()
    return jsonify({"status": "completed", "scan_id": scan_id})

@app.route('/api/reports/<int:scan_id>', methods=['GET'])
def get_report(scan_id):
    conn = get_db()
    findings = conn.execute("SELECT * FROM findings WHERE scan_id = ?", (scan_id,)).fetchall()
    return jsonify([dict(f) for f in findings])

init_db()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
