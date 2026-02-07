import os
import requests
import json
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
TARGET_REPO = os.getenv("TARGET_REPO")

def generate_backlog_item():
    """Use OpenRouter to generate a new feature/fix based on repo context."""
    if not OPENROUTER_API_KEY:
        logger.error("OPENROUTER_API_KEY not set.")
        return None

    # Get repo context (README or file list)
    # For now, we'll keep it simple and just ask for a generic improvement 
    # based on the repo name. In Phase 3 proper, we'd feed it more context.
    
    prompt = f"Given the repository {TARGET_REPO}, suggest one meaningful new feature or improvement. Output only a JSON object with 'title' and 'body' fields."
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "google/gemini-2.0-flash-001", # High quality, fast
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }
    
    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
        response.raise_for_status()
        content = response.json()['choices'][0]['message']['content']
        
        # Clean up Markdown if any
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        
        item = json.loads(content)
        return item
    except Exception as e:
        logger.error(f"Failed to generate backlog item: {e}")
        return None

def create_github_issue(item):
    """Create a new issue in the target repository."""
    if not item: return
    
    title = item.get('title')
    body = item.get('body', '')
    label = os.getenv("ISSUE_LABEL", "jules-task")
    
    cmd = f'gh issue create --repo {TARGET_REPO} --title "{title}" --body "{body}" --label "{label}"'
    
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        logger.info(f"Created new issue: {result.stdout.strip()}")
        return True
    except Exception as e:
        logger.error(f"Failed to create GitHub issue: {e}")
        return False
