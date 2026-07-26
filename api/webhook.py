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


def send_message(chat_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = reply_markup
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


def build_format_keyboard(file_id):
    buttons, row = [], []
    for fmt in SUPPORTED_FORMATS:
        row.append({"text": fmt, "callback_data": f"conv|{file_id}|{fmt}"})
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return {"inline_keyboard": buttons}


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
            file_id = msg["photo"][-1]["file_id"] if is_photo else msg["document"]["file_id"]
            send_message(chat_id, "فرمت مقصد را انتخاب کنید:", build_format_keyboard(file_id))
        elif msg.get("text") == "/start":
            send_message(
                chat_id,
                "سلام! یک عکس برای من بفرست تا فرمتش رو تغییر بدم.\n"
                "فرمت‌های پشتیبانی‌شده: " + ", ".join(SUPPORTED_FORMATS),
            )
        else:
            send_message(chat_id, "لطفاً یک تصویر ارسال کنید (به‌صورت عکس یا فایل).")

    elif "callback_query" in update:
        cq = update["callback_query"]
        chat_id = cq["message"]["chat"]["id"]
        data = cq["data"]

        try:
            _, file_id, target_format = data.split("|")
            answer_callback(cq["id"])

            file_path = get_file_path(file_id)
            image_bytes = download_telegram_file(file_path)
            converted = convert_image(image_bytes, target_format)

            ext = target_format.lower()
            send_document(chat_id, converted, f"converted.{ext}")
        except Exception as e:
            print("Conversion error:", traceback.format_exc())
            answer_callback(cq["id"], "خطا در تبدیل!")
            send_message(chat_id, f"خطا در تبدیل فرمت: {e}")


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
        self.wfile.write(b"Telegram image-convert bot is running.")
