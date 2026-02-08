import os
import db
from dotenv import load_dotenv

load_dotenv()
TARGET_REPO = os.getenv("TARGET_REPO")
print(f"TARGET_REPO: '{TARGET_REPO}'")

db.init_db()
sess = db.get_session_by_issue(14, TARGET_REPO)
print(f"Session for issue 14: {sess}")

all_sessions = db.get_session_by_issue(14, 'ajstafford/todo-app')
print(f"Session for issue 14 (hardcoded repo): {all_sessions}")
