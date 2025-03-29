import os
import json
import base64
import re
import email
from datetime import datetime, timedelta
from flask import Flask, jsonify
from telegram import Bot
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

app = Flask(__name__)

# Biến môi trường
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
TOKEN_JSON = os.getenv("TOKEN_JSON")

# Gmail API Scope
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# Tạo credentials từ token JSON
token_data = json.loads(TOKEN_JSON)
creds = Credentials.from_authorized_user_info(token_data, SCOPES)

# Tạo Gmail API service
service = build('gmail', 'v1', credentials=creds)

@app.route('/check_mail', methods=['GET'])
def check_mail():
    results = service.users().messages().list(userId='me', labelIds=['INBOX'], q='from:netflix').execute()
    messages = results.get('messages', [])

    if not messages:
        return jsonify({'message': '❌ Không tìm thấy email nào từ Netflix.'}), 200

    msg = service.users().messages().get(userId='me', id=messages[0]['id'], format='raw').execute()
    raw_data = base64.urlsafe_b64decode(msg['raw'].encode("UTF-8"))
    parsed_email = email.message_from_bytes(raw_data)

    # Lấy thông tin người gửi (email người gửi)
    from_email = parsed_email['From']
    name_match = re.search(r'\"([^\"]+)\"', from_email)
    name = name_match.group(1) if name_match else from_email.split('<')[0]

    # Lấy thời gian email được gửi
    email_time = datetime.utcfromtimestamp(int(msg['internalDate']) / 1000)
    email_time_str = email_time.strftime('%H:%M:%S')

    # Lấy body email và tìm link Netflix
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
        # Tính hiệu lực (15 phút)
        expiration_time = email_time + timedelta(minutes=15)
        expiration_str = expiration_time.strftime('%H:%M:%S')

        message = (f"📧 **Email từ**: {name}\n"
                   f"🔗 **Link nhận mã**: {target_link}\n"
                   f"🕒 **Thời gian nhận mail**: {email_time_str}\n"
                   f"⏰ **Hiệu lực**: {expiration_str}")

        Bot(token=TELEGRAM_TOKEN).send_message(chat_id=CHAT_ID, text=message)

        return jsonify({'message': f'✅ Đã gửi thông báo về {name} qua Telegram.\nLink: {target_link}\nHiệu lực: {expiration_str}'}), 200
    else:
        return jsonify({'message': '⚠️ Không tìm thấy link nhận mã trong email.'}), 200

if __name__ == '__main__':
    app.run(debug=True)
