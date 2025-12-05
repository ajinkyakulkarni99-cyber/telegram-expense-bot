import os
from datetime import datetime
import json

from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext
import gspread
from google.oauth2.service_account import Credentials

# ==== READ SETTINGS FROM HEROKU ENVIRONMENT VARIABLES ====
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
APP_URL = os.environ.get("APP_URL")  # e.g. https://your-heroku-app.herokuapp.com
GOOGLE_SERVICE_ACCOUNT = os.environ.get("GOOGLE_SERVICE_ACCOUNT")
SPREADSHEET_NAME = os.environ.get("SPREADSHEET_NAME", "ExpensesTracker")

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

worksheet = None


def get_sheet():
    """Connect to Google Sheets via the service account JSON."""
    creds_dict = json.loads(GOOGLE_SERVICE_ACCOUNT)
    credentials = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    gc = gspread.authorize(credentials)
    sh = gc.open(SPREADSHEET_NAME)
    return sh.sheet1


def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Hi! I track your expenses.\n"
        "Use me like this:\n"
        "/add food 12.50"
    )


def add(update: Update, context: CallbackContext):
    global worksheet

    if worksheet is None:
        try:
            worksheet = get_sheet()
        except Exception as e:
            update.message.reply_text("I couldn't reach the Google Sheet. Check configuration.")
            print("Error connecting to Google Sheet:", e)
            return

    # Parse category + amount
    try:
        category = context.args[0]
        amount = float(context.args[1])
    except (IndexError, ValueError):
        update.message.reply_text(
            "Oops! Use me like this:\n"
            "/add category amount\n"
            "Example: /add food 12.50"
        )
        return

    now = datetime.now().strftime("%Y-%m-%d")

    # Append a new row: DATE | CATEGORY | AMOUNT
    try:
        worksheet.append_row([now, category, amount])
    except Exception as e:
        update.message.reply_text("Couldn't save to Google Sheets. Check configuration.")
        print("Error appending row:", e)
        return

    update.message.reply_text(f"Added {amount} to {category} for {now} ✅")


def main():
    if not TOKEN or not APP_URL or not GOOGLE_SERVICE_ACCOUNT:
        raise ValueError("Missing one of TELEGRAM_BOT_TOKEN, APP_URL, or GOOGLE_SERVICE_ACCOUNT.")

    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("add", add))

    port = int(os.environ.get("PORT", 8443))

    updater.start_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=TOKEN,
    )

    webhook_url = APP_URL.rstrip("/") + "/" + TOKEN
    updater.bot.setWebhook(webhook_url)
    print("Webhook set to:", webhook_url)

    updater.idle()


if __name__ == "__main__":
    main()


