import os
import requests
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_message(text):
    """Send a simple text message via Telegram."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram notification skipped: Token or Chat ID not set.")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"Failed to send Telegram message: {e}")
        return False

def notify_session_started(issue_number, title):
    msg = f"🚀 *Session Started*\n\nIssue #{issue_number}: {title}\nJules is now working on this feature."
    send_message(msg)

def notify_pr_created(issue_number, pr_url):
    msg = f"📦 *PR Created*\n\nPR for Issue #{issue_number} is ready for review:\n{pr_url}"
    send_message(msg)

def notify_merged(issue_number, pr_number):
    msg = f"✅ *Merged*\n\nPR #{pr_number} for Issue #{issue_number} has been successfully merged!"
    send_message(msg)