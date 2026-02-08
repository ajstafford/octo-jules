import os
import json
import logging
import subprocess
import tempfile
import argparse
import random
from dotenv import load_dotenv
from openai import OpenAI

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

if os.getenv("GITHUB_TOKEN") and not os.getenv("GH_TOKEN"):
    os.environ["GH_TOKEN"] = os.getenv("GITHUB_TOKEN")

TARGET_REPO = os.getenv("TARGET_REPO")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
ISSUE_LABEL = os.getenv("ISSUE_LABEL", "jules-task")
MIN_BACKLOG_SIZE = 5
MODEL = "anthropic/claude-3.5-haiku"

def get_client():
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
    )

def run_command(command, cwd=None):
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True, cwd=cwd)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {command}\nError Output: {e.stderr}")
        return None
    except Exception as e:
        logger.error(f"Command failed: {command}\nError: {e}")
        return None

def get_repo_context():
    """Clone repo and extract meaningful context."""
    with tempfile.TemporaryDirectory() as tmpdir:
        logger.info(f"Cloning {TARGET_REPO} for context...")
        run_command(f"gh repo clone {TARGET_REPO} .", cwd=tmpdir)
        
        context = {}
        context['files'] = run_command("find . -maxdepth 2 -not -path '*/.*'", cwd=tmpdir)
        
        if os.path.exists(os.path.join(tmpdir, "README.md")):
            with open(os.path.join(tmpdir, "README.md"), 'r') as f:
                context['readme'] = f.read()[:3000]
                
        for tech_file in ["package.json", "requirements.txt", "Cargo.toml"]:
            path = os.path.join(tmpdir, tech_file)
            if os.path.exists(path):
                with open(path, 'r') as f:
                    context['tech_stack'] = f.read()
                break
                
        return context

def get_existing_issues():
    """Fetch all issues to avoid duplicates."""
    output = run_command(f'gh issue list --repo {TARGET_REPO} --state all --limit 100 --json title')
    if not output:
        return []
    return [issue['title'] for issue in json.loads(output)]

def load_personas():
    """Load personas from JSON file or return default."""
    try:
        with open("personas.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning("personas.json not found. Using default PM persona.")
        return {
            "pm": {
                "name": "Product Manager",
                "labels": [ISSUE_LABEL],
                "prompt": "You are a Product Manager. Suggest feature ideas."
            }
        }

def generate_new_ideas(context, existing_titles, persona):
    """Use OpenRouter via OpenAI SDK to generate ideas."""
    if not OPENROUTER_API_KEY:
        logger.error("OPENROUTER_API_KEY not set in environment.")
        return []

    client = get_client()
    
    if "prompt" not in persona:
        logger.error(f"Persona '{persona.get('name', 'Unknown')}' is missing a 'prompt' field in configuration.")
        return []
        
    system_prompt = persona["prompt"]
    
    prompt = f"""
{system_prompt}

TARGET REPO: {TARGET_REPO}

### Context:
Files: {context.get('files', 'Unknown')}
README: {context.get('readme', 'No README found.')}
Tech Stack: {context.get('tech_stack', 'Unknown')}

### Existing Issues (DO NOT DUPLICATE):
{", ".join(existing_titles)}

### Instructions:
1. Suggest exactly {MIN_BACKLOG_SIZE} items.
2. Output ONLY a valid JSON list of objects with "title" and "body" fields. No markdown formatting.
"""

    try:
        completion = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}]
        )
        content = completion.choices[0].message.content.strip()
        
        # Strip potential markdown code blocks
        if content.startswith("```json"):
            content = content.split("```json")[1].split("```")[0].strip()
        elif content.startswith("```"):
            content = content.split("```")[1].split("```")[0].strip()
            
        return json.loads(content)
    except Exception as e:
        logger.error(f"OpenRouter Generation failed: {e}")
        return []

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Ignore backlog size check")
    parser.add_argument("--persona", type=str, help="Specific persona key to run")
    args = parser.parse_args()

    if not TARGET_REPO:
        logger.error("TARGET_REPO not set.")
        return

    current_backlog_json = run_command(f'gh issue list --repo {TARGET_REPO} --label "{ISSUE_LABEL}" --json number')
    count = len(json.loads(current_backlog_json)) if current_backlog_json else 0
    
    logger.info(f"Current backlog count: {count}")
    
    if count == 0 or args.force:
        logger.info("Backlog low or force enabled. Generating new ideas...")
        
        personas = load_personas()
        selected_persona_key = args.persona
        
        if not selected_persona_key:
            selected_persona_key = random.choice(list(personas.keys()))
            
        if selected_persona_key not in personas:
            logger.error(f"Persona '{selected_persona_key}' not found. Using random.")
            selected_persona_key = random.choice(list(personas.keys()))
            
        persona_config = personas[selected_persona_key]
        logger.info(f"Active Persona: {persona_config['name']}")
        
        context = get_repo_context()
        existing = get_existing_issues()
        new_ideas = generate_new_ideas(context, existing, persona_config)
        
        persona_name = persona_config.get("name", "Unknown")
        
        for idea in new_ideas:
            title = idea['title']
            prefixed_title = f"[{persona_name}] {title}"
            body = idea['body']
            logger.info(f"Creating issue ({persona_name}): {prefixed_title}")
            # Only use the base ISSUE_LABEL to avoid errors with missing custom labels
            run_command(f'gh issue create --repo {TARGET_REPO} --title "{prefixed_title}" --body "{body}" --label "{ISSUE_LABEL}"')
    else:
        logger.info(f"Backlog still has {count} items. Skipping generation.")

if __name__ == "__main__":
    main()