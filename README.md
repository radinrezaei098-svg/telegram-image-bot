# ربات تلگرام تبدیل فرمت عکس (Serverless)

بات با معماری **Webhook** کار می‌کند (نه Polling)، بنابراین کاملاً با پلتفرم‌های
serverless مثل **Vercel** سازگار است. هر پیام ورودی تلگرام یک درخواست HTTP جدا
به تابع `api/webhook.py` می‌فرستد و تابع بدون هیچ حافظه‌ی بین‌درخواستی کار می‌کند.

## فرمت‌های پشتیبانی‌شده
PNG, JPEG, WEBP, BMP, GIF, ICO, TIFF

## مراحل نصب

### ۱. ساخت بات و گرفتن توکن
از [@BotFather](https://t.me/BotFather) در تلگرام یک بات بسازید و `BOT_TOKEN` را بگیرید.

### ۲. دیپلوی روی Vercel
```bash
npm i -g vercel
cd telegram-image-bot
vercel
```
بعد از دیپلوی، آدرسی مثل `https://your-project.vercel.app` می‌گیرید.

### ۳. تنظیم متغیر محیطی
در پنل Vercel (Settings → Environment Variables) مقدار زیر را اضافه کنید:
```
BOT_TOKEN=توکن_ربات_شما
```
سپس یک‌بار دیگر `vercel --prod` بزنید تا متغیر اعمال شود.

### ۴. ثبت Webhook در تلگرام
با یک درخواست (یک‌بار کافیست) به تلگرام بگویید آدرس Vercel شما را صدا بزند:
```bash
curl "https://api.telegram.org/bot<BOT_TOKEN>/setWebhook?url=https://your-project.vercel.app/api/webhook"
```

### ۵. تست
در تلگرام به بات پیام `/start` بدهید، سپس یک عکس بفرستید. بات فرمت‌های
موجود را به‌صورت دکمه نشان می‌دهد؛ با انتخاب یکی از آن‌ها، فایل تبدیل‌شده
برایتان به‌عنوان Document ارسال می‌شود.

## نکات
- به‌جای Vercel می‌توانید همین فایل `handle_update` را داخل AWS Lambda،
  Google Cloud Functions یا Cloudflare Workers (با آداپتور مناسب) هم استفاده کنید؛
  فقط لایه‌ی ورودی HTTP (کلاس `handler`) باید مطابق آن پلتفرم بازنویسی شود.
- محدودیت حجم فایل توسط Telegram Bot API حدود ۲۰ مگابایت برای دانلود است.
- برای امنیت بیشتر می‌توانید یک `secret_token` هنگام `setWebhook` تنظیم کنید
  و در `webhook.py` هدر `X-Telegram-Bot-Api-Secret-Token` را بررسی کنید.
