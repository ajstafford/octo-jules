import os
import logging
import json
import subprocess
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler
import db

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

if os.getenv("GITHUB_TOKEN") and not os.getenv("GH_TOKEN"):
    os.environ["GH_TOKEN"] = os.getenv("GITHUB_TOKEN")

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TARGET_REPO = os.getenv("TARGET_REPO")
ISSUE_LABEL = os.getenv("ISSUE_LABEL", "jules-task")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to Octo-Jules Bot!\n\n"
        "Available commands:\n"
        "/status - Show current automation status\n"
        "/add_task <title>:<body_optional> - Add a new task to backlog\n"
        "/sync - Force backlog sustainer to run"
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = db.get_connection()
    cursor = conn.execute("SELECT issue_title, state FROM sessions ORDER BY created_at DESC LIMIT 5")
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        await update.message.reply_text("No sessions recorded yet.")
        return
        
    msg = "*Recent Sessions:*\n"
    for row in rows:
        msg += f"• {row[0]}: `{row[1]}`\n"
    
    await update.message.reply_text(msg, parse_mode="Markdown")

async def add_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /add_task <title>:<body_optional>")
        return
        
    text = " ".join(context.args)
    if ":" in text:
        title, body = text.split(":", 1)
    else:
        title, body = text, ""
        
    cmd = f'gh issue create --repo {TARGET_REPO} --title "{title.strip()}" --body "{body.strip()}" --label "{ISSUE_LABEL}"'
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        await update.message.reply_text(f"✅ Issue created: {result.stdout.strip()}")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to create issue: {e}")

async def sync(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔄 Running backlog sustainer...")
    try:
        subprocess.run("python3 backlog_sustainer.py", shell=True, check=True)
        await update.message.reply_text("✅ Backlog sync complete.")
    except Exception as e:
        await update.message.reply_text(f"❌ Sync failed: {e}")

if __name__ == '__main__':
    if not TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN not set.")
    else:
        app = ApplicationBuilder().token(TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("status", status))
        app.add_handler(CommandHandler("add_task", add_task))
        app.add_handler(CommandHandler("sync", sync))
        
        print("Bot is running...")
        app.run_polling()