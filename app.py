from flask import Flask, render_template, request, jsonify
import os
import base64
import re
import email
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from telegram import Bot
import json

app = Flask(__name__)

# Lấy biến môi trường
TOKEN_JSON = os.getenv("GMAIL_TOKEN")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Parse credentials từ JSON môi trường
creds_dict = json.loads(TOKEN_JSON)
creds = Credentials.from_authorized_user_info(info=creds_dict)
service = build('gmail', 'v1', credentials=creds)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/check_mail', methods=['POST'])
def check_mail():
    data = request.json
    requested_email = data.get('email', '').strip().lower()

    if not requested_email:
        return jsonify({'message': '⚠️ Bạn phải nhập email để tiếp tục.'}), 400

    valid_subjects = [
        "Mã truy cập Netflix tạm thời của bạn",
        "Lưu ý quan trọng: Cách cập nhật Hộ gia đình Netflix",
        "Important: How to update your Netflix Household",
        "Your Netflix temporary access code"
    ]

    try:
        results = service.users().messages().list(userId='me', labelIds=['INBOX'], q='from:netflix', maxResults=10).execute()
        messages = results.get('messages', [])

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

            # Lấy nội dung HTML để tìm link
            body = ""
            if parsed_email.is_multipart():
                for part in parsed_email.walk():
                    if part.get_content_type() == "text/html":
                        body = part.get_payload(decode=True).decode(errors='ignore')
                        break
            else:
                body = parsed_email.get_payload(decode=True).decode(errors='ignore')

            links = re.findall(r'https?://[^\s"\']+', body)
            target_link = next((l for l in links if "netflix.com" in l and ("code" in l or "verify" in l)), None)

            if target_link:
                # Gửi thông báo về Telegram
                Bot(token=TELEGRAM_TOKEN).send_message(
                    chat_id=CHAT_ID,
                    text=(f"📧 Email từ: {name}\n"
                          f"📌 Tài khoản: {requested_email}\n"
                          f"🔗 Link mã: {target_link}\n"
                          f"⏱ Nhận lúc: {email_time_str}\n"
                          f"⏰ Hiệu lực: {expiration_str}")
                )

                return jsonify({
                    'success': True,
                    'account_name': name,
                    'link': target_link,
                    'received_time': email_time_str,
                    'expiration_time': expiration_str
                })

        return jsonify({'success': False, 'message': '⚠️ Không tìm thấy mã phù hợp với email đã nhập.'}), 200

    except Exception as e:
        return jsonify({'success': False, 'message': f'🚨 Lỗi: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True)
