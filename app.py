import os
import json
import base64
import re
import email
from datetime import datetime, timedelta
from flask import Flask, jsonify, render_template
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

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/check_mail', methods=['GET'])
def check_mail():
    # Các tiêu đề cần kiểm tra
    valid_subjects = [
        "Mã truy cập Netflix tạm thời của bạn",
        "Lưu ý quan trọng: Cách cập nhật Hộ gia đình Netflix",
        "Important: How to update your Netflix Household",
        "Your Netflix temporary access code"
    ]

    # Tìm email mới từ Netflix
    results = service.users().messages().list(userId='me', labelIds=['INBOX'], q='from:netflix', maxResults=10).execute()
    messages = results.get('messages', [])

    if not messages:
        return jsonify({'message': '❌ Không tìm thấy email nào từ Netflix.'}), 200

    for msg_info in messages:
        msg = service.users().messages().get(userId='me', id=msg_info['id'], format='raw').execute()
        raw_data = base64.urlsafe_b64decode(msg['raw'].encode("UTF-8"))
        parsed_email = email.message_from_bytes(raw_data)

        # ✅ Lấy tiêu đề email (subject)
        subject = parsed_email['Subject']
        if not any(subj in subject for subj in valid_subjects):
            continue  # bỏ qua nếu không đúng tiêu đề

        # ✅ Lấy người gửi
        from_email = parsed_email['From']
        name_match = re.search(r'\"([^\"]+)\"', from_email)
        name = name_match.group(1) if name_match else from_email.split('<')[0]

        # ✅ Thời gian gửi email
        email_time = datetime.utcfromtimestamp(int(msg['internalDate']) / 1000)
        email_time_str = email_time.strftime('%H:%M:%S')
        expiration_time = email_time + timedelta(minutes=15)
        expiration_str = expiration_time.strftime('%H:%M:%S')

        # ✅ Lấy nội dung email và tìm link
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
            # ✅ Gửi thông báo Telegram
            message = (f"📧 Email từ: {name}\n"
                       f"📌 Tiêu đề: {subject}\n"
                       f"🔗 Link mã: {target_link}\n"
                       f"⏱ Thời gian nhận: {email_time_str}\n"
                       f"⏰ Hiệu lực đến: {expiration_str}")
            Bot(token=TELEGRAM_TOKEN).send_message(chat_id=CHAT_ID, text=message)

            # ✅ Trả dữ liệu cho frontend
            return jsonify({
                'message': f'✅ Đã gửi mã từ {name}',
                'account_name': name,
                'link': target_link,
                'expiration_time': expiration_str,
                'received_time': email_time_str,
                'subject': subject
            }), 200

    return jsonify({'message': '⚠️ Không tìm thấy link mã hợp lệ trong email Netflix.'}), 200


if __name__ == '__main__':
    app.run(debug=True)
