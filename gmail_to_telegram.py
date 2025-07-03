import imaplib
import email
from email.header import decode_header
import re
import ssl
import time
import html
import traceback
import requests

# ========== CONFIGURA ESTO ==========
GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_PASS = os.getenv("GMAIL_PASS")  # Usa tu contraseña de aplicación o normal si no tienes 2FA

IMAP_SERVER = "imap.gmail.com"
IMAP_PORT = 993

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")  # Número que obtuviste con getUpdates()

SEARCH_KEYWORDS = ["idealista", "nuevo anuncio", "piso en alquiler"]
NUM_EMAILS = 10  # Cuántos correos recientes revisar
# ====================================

def clean_text(text):
    return html.unescape(text.strip().replace('\r', '').replace('\n', ' '))

def extract_links(text):
    return re.findall(r'https?://[^\s"]+', text)

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print("Error enviando mensaje a Telegram:", e)

def search_emails():
    context = ssl.create_default_context()
    with imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT, ssl_context=context) as mail:
        mail.login(GMAIL_USER, GMAIL_PASS)
        mail.select("inbox")

        # Buscar correos recientes
        status, messages = mail.search(None, "ALL")
        mail_ids = messages[0].split()[-NUM_EMAILS:]

        for msg_id in reversed(mail_ids):
            status, msg_data = mail.fetch(msg_id, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])

                    subject, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding or "utf-8")

                    if any(keyword.lower() in subject.lower() for keyword in SEARCH_KEYWORDS):
                        from_ = msg.get("From", "")
                        date_ = msg.get("Date", "")

                        body = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                content_type = part.get_content_type()
                                if content_type == "text/plain":
                                    body = part.get_payload(decode=True).decode(errors="ignore")
                                    break
                        else:
                            body = msg.get_payload(decode=True).decode(errors="ignore")

                        body = clean_text(body)
                        links = extract_links(body)
                        link_text = "\n".join(links)

                        message = f"<b>📬 Nuevo mensaje de Idealista</b>\n<b>Asunto:</b> {subject}\n<b>Fecha:</b> {date_}\n\n{body[:500]}..."
                        if links:
                            message += f"\n\n🔗 <b>Enlace(s):</b>\n" + link_text

                        send_telegram_message(message)
                        time.sleep(1)  # Evita ser bloqueado

