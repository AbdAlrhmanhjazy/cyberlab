from flask import Flask, render_template, request, jsonify
import requests
import os
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def check_account(platform_name, username):
    username = username.strip().replace(" ", "")
    
    try:
        if platform_name == "GitHub":
            url = f"https://api.github.com/users/{username}"
            r = requests.get(url, headers=HEADERS, timeout=4)
            if r.status_code == 200:
                data = r.json()
                return {
                    "platform": "GitHub", "category": "برمجة وتطوير", "found": True,
                    "info": f"حساب نشط: {data.get('name') or username}",
                    "link": f"https://github.com/{username}"
                }

        elif platform_name == "Telegram":
            url = f"https://t.me/{username}"
            r = requests.get(url, headers=HEADERS, timeout=4)
            # تيليجرام يضع هذا الكلاس فقط إذا كان الحساب/القناة موجودة فعلاً
            if r.status_code == 200 and 'tgme_page_extra' in r.text and 'tgme_page_title' in r.text:
                return {
                    "platform": "Telegram", "category": "تراسل فوري", "found": True,
                    "info": f"حساب أو قناة نشطة على تليجرام",
                    "link": url
                }

        elif platform_name == "Chess.com":
            url = f"https://api.chess.com/pub/player/{username}"
            r = requests.get(url, headers=HEADERS, timeout=4)
            if r.status_code == 200:
                return {
                    "platform": "Chess.com", "category": "ألعاب ورياضة", "found": True,
                    "info": f"ملف لاعب نشط",
                    "link": f"https://www.chess.com/member/{username}"
                }

        elif platform_name == "Reddit":
            url = f"https://www.reddit.com/user/{username}/about.json"
            r = requests.get(url, headers=HEADERS, timeout=4)
            if r.status_code == 200 and 'data' in r.json():
                return {
                    "platform": "Reddit", "category": "مجتمعات ونقاشات", "found": True,
                    "info": f"حساب مسجل ونشط",
                    "link": f"https://www.reddit.com/user/{username}"
                }

    except Exception:
        pass

    return {
        "platform": platform_name,
        "category": "سوشيال ميديا",
        "found": False,
        "info": f"لا يوجد حساب بهذا المعرف",
        "link": ""
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/scan', methods=['POST'])
def scan():
    data = request.json or {}
    raw_input = data.get('email', '').strip()
    if not raw_input:
        return jsonify({"error": "يرجى إدخال اسم المستخدم أو البريد"}), 400

    # تنظيف المدخلات وحذف المسافات وأي نطاق إيميل
    username = raw_input.split('@')[0].strip().replace(" ", "")

    platforms = ["GitHub", "Telegram", "Chess.com", "Reddit"]
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(check_account, p, username) for p in platforms]
        results = [f.result() for f in futures]

    found_accounts = sum(1 for r in results if r['found'])
    exposure_level = "مرتفع" if found_accounts >= 2 else ("متوسط" if found_accounts == 1 else "منخفض / لا توجد ارتباطات عامة")

    return jsonify({
        "target": raw_input,
        "username": username,
        "found_accounts": found_accounts,
        "exposure_level": exposure_level,
        "results": results
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
