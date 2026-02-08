import os
import subprocess
import json
from dotenv import load_dotenv

load_dotenv()

TARGET_REPO = os.getenv("TARGET_REPO")
ISSUE_LABEL = os.getenv("ISSUE_LABEL", "jules-task")
GH_TOKEN = os.getenv("GH_TOKEN")

print(f"Checking repo: {TARGET_REPO}")
print(f"Using label: {ISSUE_LABEL}")
print(f"Token present: {bool(GH_TOKEN)}")

cmd = f'gh issue list --repo {TARGET_REPO} --label "{ISSUE_LABEL}" --json number,title,state'
print(f"Running: {cmd}")

try:
    result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
    print("Raw Output:", result.stdout)
    items = json.loads(result.stdout)
    print(f"Found {len(items)} issues.")
    for i in items:
        print(f"- #{i['number']}: {i['title']} ({i['state']})")
except subprocess.CalledProcessError as e:
    print(f"Command failed: {e.stderr}")
except Exception as e:
    print(f"Error: {e}")
