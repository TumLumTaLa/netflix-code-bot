import os
import json
import base64
import re
import email
from io import StringIO
from flask import Flask, jsonify
from telegram import Bot
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

app = Flask(__name__)

# Lấy các biến môi trường
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
GOOGLE_CREDENTIALS = os.getenv("GOOGLE_CREDENTIALS")

# Gmail API Scope
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# Xử lý Google credentials từ biến môi trường
credentials_dict = json.loads(GOOGLE_CREDENTIALS)
flow = InstalledAppFlow.from_client_config(credentials_dict, SCOPES)
creds = flow.run_console()

# Tạo service Gmail
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

    body = ""
    if parsed_email.is_multipart():
        for part in parsed_email.walk():
            if part.get_content_type() == "text/html":
                body = part.get_payload(decode=True).decode()
                break
    else:
        body = parsed_email.get_payload(decode=True).decode()

    # Tìm link Netflix
    links = re.findall(r'https?://[^\s"\']+', body)
    target_link = next((l for l in links if "netflix.com" in l and ("code" in l or "verify" in l)), None)

    if target_link:
        Bot(token=TELEGRAM_TOKEN).send_message(chat_id=CHAT_ID, text=f"🔗 Link nhận mã Netflix:\n{target_link}")
        return jsonify({'message': f'✅ Đã gửi link: {target_link} qua Telegram.'}), 200
    else:
        return jsonify({'message': '⚠️ Không tìm thấy link nhận mã trong email.'}), 200

if __name__ == '__main__':
    app.run(debug=True)
