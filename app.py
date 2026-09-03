from flask import Flask, render_template, request, jsonify
import requests
import os
import re

app = Flask(__name__)

# قائمة مبسطة وسريعة لفحص المواقع والخدمات الشائعة عبر الاستجابة العامة
SITES = [
    {
        "name": "GitHub",
        "category": "برمجة ومطورين",
        "check_url": "https://api.github.com/legacy/user/email/{email}",
        "check_type": "status_200"
    },
    {
        "name": "Gravatar (WordPress Profile)",
        "category": "مدونات وتطبيقات الويب",
        "check_url": "https://en.gravatar.com/{hash}.json",
        "check_type": "gravatar"
    },
    {
        "name": "Adobe / Creative Cloud",
        "category": "تصميم وتطبيقات",
        "check_url": "https://auth.services.adobe.com/signin/v2/users/accounts",
        "check_type": "post_adobe"
    },
    {
        "name": "Twitter / X (Password Reset Hint)",
        "category": "شبكات اجتماعية",
        "check_url": "https://api.x.com/i/users/email_available.json?email={email}",
        "check_type": "json_taken"
    },
    {
        "name": "Spotify",
        "category": "محتوى وترفيه",
        "check_url": "https://spclient.wg.spotify.com/signup/public/v1/account?validate=1&email={email}",
        "check_type": "json_spotify"
    }
]

import hashlib

def check_gravatar(email):
    email_hash = hashlib.md5(email.strip().lower().encode('utf-8')).hexdigest()
    url = f"https://en.gravatar.com/{email_hash}.json"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=3)
        if r.status_code == 200:
            data = r.json()
            entry = data.get('entry', [{}])[0]
            profile_url = entry.get('profileUrl', f"https://gravatar.com/{email_hash}")
            username = entry.get('preferredUsername', 'حساب نشط')
            return {"exists": True, "details": f"مستخدم نشط: {username}", "link": profile_url}
    except Exception:
        pass
    return {"exists": False}

def check_spotify(email):
    url = f"https://spclient.wg.spotify.com/signup/public/v1/account?validate=1&email={email}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=3)
        # status 20 indicates email exists on Spotify
        if r.status_code == 200 and r.json().get('status') == 20:
            return {"exists": True, "details": "البريد مسجل ولديه حساب نشط", "link": "https://open.spotify.com"}
    except Exception:
        pass
    return {"exists": False}

def check_github(email):
    url = f"https://api.github.com/search/users?q={email}+in:email"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=3)
        if r.status_code == 200:
            data = r.json()
            if data.get('total_count', 0) > 0:
                user = data['items'][0]['login']
                return {"exists": True, "details": f"حساب عام مرتبط: @{user}", "link": f"https://github.com/{user}"}
    except Exception:
        pass
    return {"exists": False}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/scan', methods=['POST'])
def scan_email():
    data = request.json or {}
    email = data.get('email', '').strip().lower()
    
    if not email or not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return jsonify({"error": "يرجى كتابة عنوان بريد إلكتروني صالح ومكتمل"}), 400

    results = []

    # فحص المنصات المباشرة
    # 1. GitHub
    gh = check_github(email)
    results.append({
        "platform": "GitHub Developer Network",
        "category": "أدوات برمجية وتطوير",
        "found": gh["exists"],
        "info": gh.get("details", "لا يوجد حساب عام بهذا البريد"),
        "link": gh.get("link", "")
    })

    # 2. Gravatar
    gv = check_gravatar(email)
    results.append({
        "platform": "Gravatar (Wordpress & Tech Network)",
        "category": "شبكات تقنية ومواقع شخصية",
        "found": gv["exists"],
        "info": gv.get("details", "لا توجد بصمة مسجلة في شبكة ووردبريس"),
        "link": gv.get("link", "")
    })

    # 3. Spotify
    sp = check_spotify(email)
    results.append({
        "platform": "Spotify",
        "category": "منصات البث والوسائط",
        "found": sp["exists"],
        "info": sp.get("details", "البريد غير مستخدم كحساب مسجل"),
        "link": sp.get("link", "")
    })

    # 4. محاكاة فحص تسريبات الأمان (Breach Intelligence)
    # تقييم النطاق (Domain Assessment)
    domain = email.split('@')[1]
    is_corporate = domain not in ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com']
    
    results.append({
        "platform": "Domain & Mail MX Records",
        "category": "البنية التحتية للخادم",
        "found": True,
        "info": f"نطاق البريد: {domain} ({'بريد مؤسسي/خاص' if is_corporate else 'مزود بريد عام مجاني'})",
        "link": f"https://{domain}"
    })

    # إحصائيات
    found_count = sum(1 for r in results if r['found'] and r['platform'] != "Domain & Mail MX Records")
    risk_level = "مرتفع (بصمة رقمية منتشرة)" if found_count >= 2 else ("متوسط" if found_count == 1 else "منخفض / بريد حديث أو محمي")

    return jsonify({
        "email": email,
        "found_accounts": found_count,
        "exposure_level": risk_level,
        "results": results
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
