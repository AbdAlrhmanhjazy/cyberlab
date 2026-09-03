from flask import Flask, render_template, request, jsonify
import requests
import os
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)

SOCIAL_PLATFORMS = [
    {"name": "Telegram", "category": "تراسل فوري", "url_template": "https://t.me/{}", "check_type": "telegram"},
    {"name": "GitHub", "category": "برمجة وتطوير", "url_template": "https://github.com/{}", "check_type": "status_code"},
    {"name": "TikTok", "category": "فيديو وشبكات اجتماعية", "url_template": "https://www.tiktok.com/@{}", "check_type": "status_code"},
    {"name": "Pinterest", "category": "محتوى وصور", "url_template": "https://www.pinterest.com/{}/", "check_type": "status_code"},
    {"name": "Reddit", "category": "مجتمعات ونقاشات", "url_template": "https://www.reddit.com/user/{}", "check_type": "status_code"},
    {"name": "Chess.com", "category": "ألعاب ورياضة ذهنية", "url_template": "https://api.chess.com/pub/player/{}", "check_type": "status_code"},
    {"name": "SoundCloud", "category": "صوتيات وموسيقى", "url_template": "https://soundcloud.com/{}", "check_type": "status_code"}
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

def check_target_platform(platform, username):
    url = platform["url_template"].format(username)
    check_type = platform["check_type"]
    try:
        if check_type == "status_code":
            r = requests.get(url, headers=HEADERS, timeout=4, allow_redirects=False)
            if r.status_code == 200:
                return {"platform": platform["name"], "category": platform["category"], "found": True, "info": f"حساب نشط: @{username}", "link": url}
        elif check_type == "telegram":
            r = requests.get(url, headers=HEADERS, timeout=4)
            if r.status_code == 200 and 'tgme_page_extra' in r.text:
                return {"platform": "Telegram", "category": platform["category"], "found": True, "info": f"حساب تليجرام نشط: @{username}", "link": url}
    except Exception:
        pass

    return {"platform": platform["name"], "category": platform["category"], "found": False, "info": f"غير مسجل بالمعرف @{username}", "link": ""}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/scan', methods=['POST'])
def scan():
    data = request.json or {}
    raw_input = data.get('email', '').strip()
    if not raw_input:
        return jsonify({"error": "يرجى كتابة البريد أو المعرف"}), 400

    username = raw_input.split('@')[0].strip() if '@' in raw_input else raw_input

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(check_target_platform, p, username) for p in SOCIAL_PLATFORMS]
        results = [f.result() for f in futures]

    found_accounts = sum(1 for r in results if r['found'])
    exposure_level = "مرتفع" if found_accounts >= 2 else ("متوسط" if found_accounts == 1 else "منخفض")

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
