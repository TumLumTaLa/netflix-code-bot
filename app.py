from flask import Flask, render_template, request, jsonify
import base64
import re
import email
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from telegram import Bot
import os

app = Flask(__name__)

# Load credentials từ biến môi trường hoặc file token.json
creds = Credentials.from_authorized_user_file('token.json', scopes=['https://www.googleapis.com/auth/gmail.readonly'])
service = build('gmail', 'v1', credentials=creds)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN") or "7673446907:AAE6aUOgK4Z0yv9r3R3VvyxEtZD5L84Gx-I"
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID") or "-4790587221"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/check_mail', methods=['GET'])
def check_mail():
    requested_email = request.args.get('email', '').strip().lower()
    if not requested_email:
        return jsonify({'message': '⚠️ Bạn phải nhập email để tiếp tục.'}), 400

    valid_subjects = [
        "Mã truy cập Netflix tạm thời của bạn",
        "Lưu ý quan trọng: Cách cập nhật Hộ gia đình Netflix",
        "Important: How to update your Netflix Household",
        "Your Netflix temporary access code"
    ]

    results = service.users().messages().list(userId='me', labelIds=['INBOX'], q='from:netflix', maxResults=10).execute()
    messages = results.get('messages', [])

    if not messages:
        return jsonify({'message': '❌ Không tìm thấy email nào từ Netflix.'}), 200

    for msg_info in messages:
        msg = service.users().messages().get(userId='me', id=msg_info['id'], format='raw').execute()
        raw_data = base64.urlsafe_b64decode(msg['raw'].encode("UTF-8"))
        parsed_email = email.message_from_bytes(raw_data)

        subject = parsed_email['Subject']
        if not any(subj in subject for subj in valid_subjects):
            continue

        to_field = parsed_email['To'].lower() if parsed_email['To'] else ""
        if requested_email not in to_field:
            continue

        from_email = parsed_email['From']
        name_match = re.search(r'"([^"]+)"', from_email)
        name = name_match.group(1) if name_match else from_email.split('<')[0]

        email_time = datetime.utcfromtimestamp(int(msg['internalDate']) / 1000)
        email_time_str = email_time.strftime('%H:%M:%S')
        expiration_str = (email_time + timedelta(minutes=15)).strftime('%H:%M:%S')

        body = ""
        if parsed_email.is_multipart():
            for part in parsed_email.walk():
                if part.get_content_type() == "text/html":
                    body = part.get_payload(decode=True).decode()
                    break
        else:
            body = parsed_email.get_payload(decode=True).decode()

        links = re.findall(r'https?://[^\s"\']+', body)
        target_link = next((l for l in links if "netflix.com" in l and ("code" in l or "verify" in l)), None)

        if target_link:
            Bot(token=TELEGRAM_TOKEN).send_message(
                chat_id=CHAT_ID,
                text=(f"📧 Email từ: {name}\n"
                      f"📌 Cho tài khoản: {requested_email}\n"
                      f"🔗 Link mã: {target_link}\n"
                      f"⏱ Nhận lúc: {email_time_str}\n"
                      f"⏰ Hiệu lực: {expiration_str}")
            )

            return jsonify({
                'message': f'✅ Đã gửi mã từ {requested_email} qua Telegram.',
                'account_name': name,
                'link': target_link,
                'expiration_time': expiration_str,
                'received_time': email_time_str
            }), 200

    return jsonify({'message': '⚠️ Không tìm thấy mã phù hợp với email đã nhập.'}), 200

if __name__ == '__main__':
    app.run(debug=True)
