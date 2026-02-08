import os
import subprocess
import json
import time
import logging
import requests
from dotenv import load_dotenv
import db
import notifier

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

# Alias GITHUB_TOKEN to GH_TOKEN for the gh CLI if necessary
if os.getenv("GITHUB_TOKEN") and not os.getenv("GH_TOKEN"):
    os.environ["GH_TOKEN"] = os.getenv("GITHUB_TOKEN")

TARGET_REPO = os.getenv("TARGET_REPO")
ISSUE_LABEL = os.getenv("ISSUE_LABEL", "jules-task")
MANUAL_MODE = os.getenv("MANUAL_MODE", "false").lower() == "true"
SLEEP_INTERVAL = int(os.getenv("SLEEP_INTERVAL", "300"))
JULES_API_KEY = os.getenv("JULES_API_KEY")

JULES_API_BASE = "https://jules.googleapis.com/v1alpha"

# Track retries for merging COMPLETED sessions
merge_retries = {}

def run_command(command, cwd=None):
    """Run a shell command and return the output."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            capture_output=True,
            text=True,
            cwd=cwd
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {command}\nError: {e.stderr}")
        return None

def fetch_open_issues():
    """Fetch all open issues with the target label."""
    query = f'gh issue list --repo {TARGET_REPO} --label "{ISSUE_LABEL}" --json number,title,body'
    output = run_command(query)
    if not output:
        return []
    return json.loads(output)

def fetch_next_issue():
    """Fetch the next issue based on user selection via Telegram."""
    logger.info("Checking for next task...")
    
    # 1. Check if user selected an issue
    selected_id = db.get_setting('next_issue')
    if selected_id:
        logger.info(f"User selected issue #{selected_id}")
        db.delete_setting('next_issue')
        db.delete_setting('waiting_for_input')
        
        cmd = f'gh issue view {selected_id} --repo {TARGET_REPO} --json number,title,body'
        out = run_command(cmd)
        if out:
            return json.loads(out)
        else:
            logger.error(f"Selected issue #{selected_id} not found.")
            return None

    # 2. Check if we are already waiting for input
    if db.get_setting('waiting_for_input') == 'true':
        logger.info("Waiting for user selection...")
        return None

    # 3. Fetch open issues and prompt user
    issues = fetch_open_issues()
    if not issues:
        logger.info("No open issues found in backlog.")
        return None
    
    valid_issues = []
    for issue in issues:
        # Check if issue is already in progress
        sess = db.get_session_by_issue(issue['number'], TARGET_REPO)
        if not sess or sess[4] in ['MERGED', 'FAILED']: # state index is 4
            valid_issues.append(issue)
            
    if not valid_issues:
        logger.info("All open issues are already processed or in progress.")
        return None

    # Construct prompt message
    msg = "📋 *Select Next Task*\n\n"
    for i in valid_issues[:10]:
        msg += f"• *#{i['number']}*: {i['title']}\n"
    msg += "\nReply with `/pick <number>` to start."
    
    notifier.send_message(msg)
    db.set_setting('waiting_for_input', 'true')
    return None

def get_repo_info():
    """Get the source name and default branch for the target repo."""
    headers = {"x-goog-api-key": JULES_API_KEY}
    try:
        response = requests.get(f"{JULES_API_BASE}/sources", headers=headers)
        response.raise_for_status()
        sources = response.json().get('sources', [])
        
        owner, repo = TARGET_REPO.split('/')
        for src in sources:
            gr = src.get('githubRepo', {})
            if gr.get('owner') == owner and gr.get('repo') == repo:
                source_name = src['name']
                default_branch = gr.get('defaultBranch', {}).get('displayName', 'main')
                return source_name, default_branch
        
        logger.error(f"Source for {TARGET_REPO} not found in Jules.")
        return None, None
    except Exception as e:
        logger.error(f"Failed to fetch sources: {e}")
        return None, None

def find_existing_session(title):
    """Check if there's an existing session for this issue on Jules API."""
    headers = {"x-goog-api-key": JULES_API_KEY}
    try:
        response = requests.get(f"{JULES_API_BASE}/sessions?pageSize=20", headers=headers)
        response.raise_for_status()
        sessions = response.json().get('sessions', [])
        for s in sessions:
            if s.get('title') == title and s.get('state') not in ["COMPLETED", "FAILED"]:
                sid = s.get('id') or s.get('name').split('/')[-1]
                return sid
        return None
    except Exception as e:
        logger.error(f"Failed to check existing sessions: {e}")
        return None

def run_jules_api_session(issue, session_id=None):
    """Invoke Jules via REST API and poll for completion."""
    issue_number = issue['number']
    issue_title = issue['title']
    session_title = f"Fix Issue #{issue_number}"
    
    # Check for existing session in DB first if not provided
    if not session_id:
        existing_db_sess = db.get_session_by_issue(issue_number, TARGET_REPO)
        if existing_db_sess and existing_db_sess[4] not in ["MERGED", "FAILED"]:
            session_id = existing_db_sess[0]
            logger.info(f"Resuming session {session_id} from DB for Issue #{issue_number}")
    else:
         logger.info(f"Resuming specific session {session_id} for Issue #{issue_number}")

    if not session_id:
        # Check Jules API for any non-terminal session with this title
        existing_id = find_existing_session(session_title)
        if existing_id:
            logger.info(f"Found active Jules session {existing_id} for {session_title}. Resuming.")
            session_id = existing_id
        else:
            source_name, default_branch = get_repo_info()
            if not source_name:
                return None

            logger.info(f"Starting NEW Jules API session for Issue #{issue_number}")
            notifier.notify_session_started(issue_number, issue_title)
            
            headers = {
                "x-goog-api-key": JULES_API_KEY,
                "Content-Type": "application/json"
            }
            
            payload = {
                "prompt": f"Fix Issue #{issue_number}: {issue_title}\n\n{issue.get('body', '')}",
                "sourceContext": {
                    "source": source_name,
                    "githubRepoContext": {
                        "startingBranch": default_branch
                    }
                },
                "automationMode": "AUTO_CREATE_PR",
                "title": session_title
            }
            
            try:
                response = requests.post(f"{JULES_API_BASE}/sessions", headers=headers, json=payload)
                response.raise_for_status()
                session = response.json()
                session_id = session['id']
                logger.info(f"Session {session_id} created. Polling...")
            except Exception as e:
                logger.error(f"API Request failed: {e}")
                return None

    # Track in DB
    db.save_session(session_id, issue_number, issue_title, TARGET_REPO, "IN_PROGRESS")

    # Common Polling Logic
    headers = {"x-goog-api-key": JULES_API_KEY}
    while True:
        # Check if we should pause while polling
        if db.is_paused():
            logger.info("Orchestrator paused. Waiting 30s...")
            time.sleep(30)
            continue

        try:
            status_res = requests.get(f"{JULES_API_BASE}/sessions/{session_id}", headers=headers)
            status_res.raise_for_status()
            session_data = status_res.json()
            state = session_data.get('state')
            
            logger.info(f"Session {session_id} state: {state}")
            db.update_session_state(session_id, state)
            
            if state == "COMPLETED":
                logger.info(f"Session {session_id} completed!")
                return session_data
            elif state == "FAILED":
                logger.error(f"Session {session_id} failed.")
                db.update_session_state(session_id, "FAILED")
                notifier.notify_failed(issue_number, session_id)
                db.set_paused(True)
                return None
                
            time.sleep(60)
        except Exception as e:
            logger.error(f"Polling failed: {e}")
            time.sleep(30)

def check_pr_status(issue_number, session_data=None, notify=False):
    """Check if the PR for the issue has been manually merged."""
    logger.info(f"Checking PR status for Issue #{issue_number}...")
    
    # Use --state all and --limit to find recent PRs (merged or open)
    # Search by issue number is unreliable if title doesn't contain it.
    find_pr_cmd = f'gh pr list --repo {TARGET_REPO} --state all --limit 50 --json number,url,title,headRefName,state'
    pr_output = run_command(find_pr_cmd)
    
    if not pr_output:
        return False
        
    prs = json.loads(pr_output)
    target_pr = None
    
    session_id = None
    if isinstance(session_data, dict):
        session_id = session_data.get('id')
    elif isinstance(session_data, str):
        session_id = session_data

    for pr in prs:
        title = pr['title'].lower()
        branch = pr['headRefName'].lower()
        issue_ref = f"#{issue_number}"
        
        if session_id and str(session_id) in branch:
            target_pr = pr
            break
            
        if issue_ref in title or f"issue-{issue_number}" in branch or "jules" in branch:
            target_pr = pr
            break
            
    if not target_pr:
        logger.warning(f"No PR found for Issue #{issue_number}")
        return False
        
    pr_number = target_pr['number']
    pr_url = target_pr['url']
    
    # Notify if first time seeing PR
    if session_id:
        db.update_session_pr(session_id, pr_number, pr_url)

    view_cmd = f'gh pr view {pr_number} --repo {TARGET_REPO} --json state,url'
    view_out = run_command(view_cmd)
    if view_out:
        pr_details = json.loads(view_out)
        state = pr_details['state'] # OPEN, MERGED, CLOSED
        
        if state == "MERGED":
            logger.info(f"PR #{pr_number} is MERGED.")
            notifier.notify_merged(issue_number, pr_number)
            
            if session_id:
                db.update_session_state(session_id, "MERGED")
            
            close_issue_cmd = f'gh issue close {issue_number} --repo {TARGET_REPO} --comment "Merged via automation in PR #{pr_number}"'
            run_command(close_issue_cmd)
            return True
            
        elif state == "OPEN":
            logger.info(f"PR #{pr_number} is OPEN. Waiting for manual merge.")
            if notify:
                notifier.notify_pr_ready_for_review(issue_number, pr_url)
            return False

    return False

def process_one_active_session():
    """Resume and finish ONE active session if exists. Returns True if work was done."""
    active = db.get_active_sessions(TARGET_REPO)
    if not active:
        return False
        
    sess = active[0]
    session_id, issue_number, title, repo, state = sess[0], sess[1], sess[2], sess[3], sess[4]
    
    if state == "COMPLETED":
        logger.info(f"Session {session_id} (Issue #{issue_number}) is COMPLETED. Waiting for manual merge...")
        if check_pr_status(issue_number, session_id):
            logger.info(f"Session {session_id} manually merged and finalized.")
            return True
        else:
            # PR is still open. We block here. 
            # We return True to indicate "work is pending" (waiting), 
            # so the main loop doesn't sleep for full interval or pick new tasks.
            # But we should sleep a bit to avoid hot-looping the API.
            logger.info("PR not yet merged. Sleeping 60s...")
            time.sleep(60)
            return True

    logger.info(f"Resuming active session: {session_id} (Issue #{issue_number}, State: {state})")
    session_data = run_jules_api_session({'number': issue_number, 'title': title}, session_id=session_id)
    if session_data:
        logger.info("Waiting 20s for PR propagation...")
        time.sleep(20)
        check_pr_status(issue_number, session_data, notify=True)
    
    return True

def main():
    if not TARGET_REPO:
        logger.error("TARGET_REPO not set in environment.")
        return

    db.init_db()
    single_run = os.getenv("SINGLE_RUN", "false").lower() == "true"
    logger.info(f"Starting Octo-Jules for {TARGET_REPO} (single_run={single_run})")
    
    while True:
        # CHECK IF PAUSED
        if db.is_paused():
            logger.info("Orchestrator is PAUSED via database setting. Sleeping...")
            time.sleep(60)
            continue

        if process_one_active_session():
            if single_run: break
            continue
        
        issue = fetch_next_issue()
        if issue:
            session_data = run_jules_api_session(issue)
            if session_data:
                logger.info("Waiting 20s for PR to propagate...")
                time.sleep(20)
                check_pr_status(issue['number'], session_data, notify=True)
        else:
            logger.info("Nothing to do.")
            if single_run: break
            
        if single_run: break
        logger.info(f"Sleeping for {SLEEP_INTERVAL}s...")
        time.sleep(SLEEP_INTERVAL)

if __name__ == "__main__":
    main()
