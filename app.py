from flask import Flask, jsonify
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from telegram import Bot
import base64
import os
import re
import email

app = Flask(__name__)

# Bot info
TELEGRAM_TOKEN = "7673446907:AAE6aUOgK4Z0yv9r3R3VvyxEtZD5L84Gx-I"
CHAT_ID = "1794706168"

# Gmail API
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
creds = None

if os.path.exists('token.json'):
    creds = Credentials.from_authorized_user_file('token.json', SCOPES)
else:
    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
    creds = flow.run_local_server(port=0)
    with open('token.json', 'w') as token:
        token.write(creds.to_json())

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

    # Tìm tất cả đường link trong email HTML
    links = re.findall(r'https?://[^\s"\']+', body)

    # Tìm link chứa "netflix" hoặc có chữ "code", hoặc có dạng /verify/
    target_link = next((l for l in links if "netflix.com" in l and ("code" in l or "verify" in l)), None)

    if target_link:
        Bot(token=TELEGRAM_TOKEN).send_message(chat_id=CHAT_ID, text=f"🔗 Link nhận mã Netflix:\n{target_link}")
        return jsonify({'message': f'✅ Đã gửi link: {target_link} qua Telegram.'}), 200
    else:
        return jsonify({'message': '⚠️ Không tìm thấy link nhận mã trong email.'}), 200

if __name__ == '__main__':
    app.run(debug=True)
