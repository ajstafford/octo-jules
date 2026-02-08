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

def get_main_keyboard():
    paused = db.is_paused()
    pause_label = "▶️ Resume" if paused else "⏸ Pause"
    pause_callback = "resume" if paused else "pause"
    
    keyboard = [
        [
            InlineKeyboardButton("📊 Status", callback_data="status"),
            InlineKeyboardButton("🔄 Sync Backlog", callback_data="sync")
        ],
        [
            InlineKeyboardButton(pause_label, callback_data=pause_callback),
            InlineKeyboardButton("➕ Add Task", callback_data="ask_task")
        ],
        [InlineKeyboardButton("🗑 Clear Finished", callback_data="clear_terminal")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🐙 *Octo-Jules Control Center*\n\nManage your autonomous coding agent from here.",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "status":
        conn = db.get_connection()
        cursor = conn.execute("SELECT issue_title, state FROM sessions ORDER BY created_at DESC LIMIT 5")
        rows = cursor.fetchall()
        conn.close()
        
        paused = db.is_paused()
        msg = f"*Current State:* {'⏸ PAUSED' if paused else '🚀 RUNNING'}\n\n*Recent Sessions:*\n"
        if not rows:
            msg += "No sessions yet."
        else:
            for row in rows:
                msg += f"• {row[0]}: `{row[1]}`\n"
        
        await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=get_main_keyboard())

    elif data == "pause":
        db.set_paused(True)
        await query.edit_message_text("⏸ Orchestrator has been *PAUSED*.", parse_mode="Markdown", reply_markup=get_main_keyboard())
        
    elif data == "resume":
        db.set_paused(False)
        await query.edit_message_text("🚀 Orchestrator has been *RESUMED*.", parse_mode="Markdown", reply_markup=get_main_keyboard())

    elif data == "sync":
        await query.message.reply_text("🔄 Triggering backlog sustainer...")
        try:
            subprocess.run("python3 backlog_sustainer.py", shell=True, check=True)
            await query.message.reply_text("✅ Backlog sync complete.")
        except Exception as e:
            await query.message.reply_text(f"❌ Sync failed: {e}")

    elif data == "ask_task":
        await query.message.reply_text("Send the task in this format:\n`/add_task Title:Body`", parse_mode="Markdown")

    elif data == "clear_terminal":
        # Optional utility to hide old merged items from dashboard/bot
        await query.message.reply_text("Cleaning up terminal states in database...")
        # Add logic here if needed

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

if __name__ == '__main__':
    if not TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN not set.")
    else:
        app = ApplicationBuilder().token(TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("add_task", add_task))
        app.add_handler(CommandHandler("status", lambda u, c: start(u, c))) # Alias /status to /start for keyboard
        app.add_handler(CallbackQueryHandler(button_handler))
        
        print("Bot is running...")
        app.run_polling()
