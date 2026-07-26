import os
import io
import json
import traceback
import requests
from http.server import BaseHTTPRequestHandler
from PIL import Image

BOT_TOKEN = os.environ.get("BOT_TOKEN")
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
TELEGRAM_FILE_API = f"https://api.telegram.org/file/bot{BOT_TOKEN}"

SUPPORTED_FORMATS = ["PNG", "JPEG", "WEBP", "BMP", "GIF", "ICO", "TIFF"]


def send_message(chat_id, text, reply_markup=None, reply_to_message_id=None):
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    if reply_to_message_id:
        payload["reply_to_message_id"] = reply_to_message_id
    r = requests.post(f"{TELEGRAM_API}/sendMessage", json=payload, timeout=15)
    print("sendMessage response:", r.status_code, r.text)


def answer_callback(callback_query_id, text=None):
    payload = {"callback_query_id": callback_query_id}
    if text:
        payload["text"] = text
    requests.post(f"{TELEGRAM_API}/answerCallbackQuery", json=payload, timeout=15)


def get_file_path(file_id):
    r = requests.get(f"{TELEGRAM_API}/getFile", params={"file_id": file_id}, timeout=15).json()
    print("getFile response:", r)
    return r["result"]["file_path"]


def download_telegram_file(file_path):
    r = requests.get(f"{TELEGRAM_FILE_API}/{file_path}", timeout=30)
    return r.content


def send_document(chat_id, file_bytes, filename):
    files = {"document": (filename, file_bytes)}
    r = requests.post(
        f"{TELEGRAM_API}/sendDocument",
        data={"chat_id": chat_id},
        files=files,
        timeout=60,
    )
    print("sendDocument response:", r.status_code, r.text)


def build_format_keyboard():
    # نکته مهم: callback_data تلگرام حداکثر ۶۴ بایت مجازه.
    # پس دیگه file_id رو اینجا نمی‌ذاریم، فقط فرمت مقصد رو می‌فرستیم
    # و file_id رو موقع callback از روی reply_to_message می‌گیریم.
    buttons, row = [], []
    for fmt in SUPPORTED_FORMATS:
        row.append({"text": fmt, "callback_data": f"conv|{fmt}"})
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return {"inline_keyboard": buttons}


def extract_file_id(msg):
    """از یک پیام تلگرام (عکس یا فایل تصویری) file_id رو استخراج می‌کنه."""
    if "photo" in msg:
        return msg["photo"][-1]["file_id"]
    if "document" in msg:
        return msg["document"]["file_id"]
    return None


def convert_image(image_bytes, target_format):
    img = Image.open(io.BytesIO(image_bytes))
    if target_format in ("JPEG", "BMP") and img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    out = io.BytesIO()
    save_kwargs = {}
    if target_format == "JPEG":
        save_kwargs["quality"] = 95
    img.save(out, format=target_format, **save_kwargs)
    out.seek(0)
    return out.read()


def handle_update(update):
    print("Received update:", json.dumps(update))

    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]

        is_photo = "photo" in msg
        is_image_doc = "document" in msg and str(
            msg["document"].get("mime_type", "")
        ).startswith("image/")

        print("is_photo:", is_photo, "is_image_doc:", is_image_doc)

        if is_photo or is_image_doc:
            send_message(
                chat_id,
                "باحاله! 😍 حالا بگو می‌خوای چه فرمتی تبدیلش کنم 👇",
                reply_markup=build_format_keyboard(),
                reply_to_message_id=msg["message_id"],
            )
        elif msg.get("text") == "/start":
            send_message(
                chat_id,
                "سلاااام! 👋 من ربات تبدیل فرمت عکسم 🖼️✨\n"
                "یه عکس یا فایل تصویری برام بفرست تا فرمتش رو عوض کنم.\n"
                "فرمت‌های پشتیبانی‌شده: " + ", ".join(SUPPORTED_FORMATS) + " 🎨",
            )
        else:
            send_message(chat_id, "یه عکس یا فایل تصویری بفرست تا برات تبدیلش کنم 📸📁")

    elif "callback_query" in update:
        cq = update["callback_query"]
        chat_id = cq["message"]["chat"]["id"]
        data = cq["data"]

        try:
            _, target_format = data.split("|")

            original_msg = cq["message"].get("reply_to_message")
            file_id = extract_file_id(original_msg) if original_msg else None

            if not file_id:
                answer_callback(cq["id"], "پیام اصلی رو پیدا نکردم 😕")
                send_message(chat_id, "اوه! فکر کنم پیام اصلی عکس پاک شده یا خیلی قدیمیه، دوباره برام بفرستش 🙏")
                return

            answer_callback(cq["id"], "چشم، دارم درستش می‌کنم... ⏳")

            file_path = get_file_path(file_id)
            image_bytes = download_telegram_file(file_path)
            converted = convert_image(image_bytes, target_format)

            ext = target_format.lower()
            send_document(chat_id, converted, f"converted.{ext}")
            send_message(chat_id, f"تمومه! فایلت به فرمت {target_format} آماده‌ست 🎉")
        except Exception as e:
            print("Conversion error:", traceback.format_exc())
            answer_callback(cq["id"], "یه مشکلی پیش اومد! 😅")
            send_message(chat_id, f"اوپس، تو تبدیل فرمت خطا خوردم: {e} 🙈")


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length else b"{}"

        try:
            update = json.loads(body or b"{}")
            handle_update(update)
        except Exception:
            print("Error handling update:", traceback.format_exc())

        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Telegram image-convert bot is running. \xf0\x9f\xa4\x96")
