from flask import Flask, render_template, request, jsonify
import sqlite3
import socket
import time
import os

app = Flask(__name__)
DB_NAME = "cyberlab.db"

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS monitored_assets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                host TEXT NOT NULL,
                status TEXT DEFAULT 'OFFLINE',
                latency_ms INTEGER DEFAULT 0,
                last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS security_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                source_ip TEXT NOT NULL,
                target_asset TEXT NOT NULL,
                severity TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # إضافة سجلات استشعارية افتراضية للمحاكاة
        count = conn.execute("SELECT COUNT(*) as c FROM security_logs").fetchone()['c']
        if count == 0:
            conn.execute("""
                INSERT INTO security_logs (event_type, source_ip, target_asset, severity, message)
                VALUES 
                ('PORT_SWEEP', '192.168.1.104', 'Command Center Server', 'HIGH', 'محاولة مسح منافذ متسلسلة غير مصرح بها'),
                ('AUTH_FAILURE', '45.133.1.20', 'Auth Gateway', 'CRITICAL', 'تكرار محاولات دخول فاشلة (Brute Force detected)'),
                ('UNUSUAL_TRAFFIC', '192.168.1.55', 'HQ Router', 'MEDIUM', 'ارتفاع مفاجئ في حركة البيانات خارج أوقات العمل')
            """)
            conn.commit()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/assets', methods=['GET', 'POST'])
def handle_assets():
    conn = get_db()
    cursor = conn.cursor()
    if request.method == 'POST':
        data = request.json
        cursor.execute("INSERT INTO monitored_assets (name, host) VALUES (?, ?)", (data['name'], data['host']))
        conn.commit()
        return jsonify({"status": "success", "id": cursor.lastrowid})
    else:
        assets = cursor.execute("SELECT * FROM monitored_assets").fetchall()
        return jsonify([dict(a) for a in assets])

@app.route('/api/assets/ping/<int:asset_id>', methods=['POST'])
def ping_asset(asset_id):
    conn = get_db()
    cursor = conn.cursor()
    asset = cursor.execute("SELECT * FROM monitored_assets WHERE id = ?", (asset_id,)).fetchone()
    if not asset:
        return jsonify({"error": "Asset not found"}), 404

    host = asset['host']
    status = 'OFFLINE'
    latency = 0
    ports_to_try = [80, 443, 22, 53]
    
    start = time.time()
    reachable = False
    for p in ports_to_try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.6)
        res = s.connect_ex((host, p))
        s.close()
        if res == 0:
            reachable = True
            break
            
    if reachable:
        latency = int((time.time() - start) * 1000)
        status = 'ONLINE'
    else:
        # فحص بديل عبر حل الاسم (DNS) للتأكد من وجود الخادم
        try:
            socket.gethostbyname(host)
            latency = int((time.time() - start) * 1000)
            status = 'ONLINE'
        except Exception:
            status = 'OFFLINE'
            latency = 0

    cursor.execute("""
        UPDATE monitored_assets 
        SET status = ?, latency_ms = ?, last_checked = CURRENT_TIMESTAMP 
        WHERE id = ?
    """, (status, latency, asset_id))
    
    # إذا كان السيرفر أوفلاين يتم إطلاق تنبيه في سجلات الرصد
    if status == 'OFFLINE':
        cursor.execute("""
            INSERT INTO security_logs (event_type, source_ip, target_asset, severity, message)
            VALUES ('NODE_DOWN', 'SYSTEM_MONITOR', ?, 'HIGH', 'انقطاع الاتصال بنقطة اتصال استراتيجية')
        """, (asset['name'],))

    conn.commit()
    return jsonify({"id": asset_id, "status": status, "latency": latency})

@app.route('/api/logs', methods=['GET'])
def get_logs():
    conn = get_db()
    logs = conn.execute("SELECT * FROM security_logs ORDER BY id DESC LIMIT 20").fetchall()
    return jsonify([dict(l) for l in logs])

init_db()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
