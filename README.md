# Octo-Jules 🐙

Octo-Jules is an autonomous development loop that leverages Google's **Jules API** to implement features and fixes directly from your GitHub Issues backlog. It manages the lifecycle of a task from issue selection to PR creation, waiting for your manual review and merge.

## 🚀 Features

- **Autonomous Orchestrator**: Fetches prioritized issues and triggers Jules coding sessions.
- **Manual Control**: The system waits for your approval before starting work and before merging PRs. It will never merge code without your explicit action on GitHub.
- **Interactive Selection**: Choose which issue Jules works on next directly from Telegram.
- **Backlog Sustainer**: Uses LLMs (via OpenRouter) to analyze your codebase and automatically generate new feature ideas.
- **Real-time Monitoring**: Streamlit dashboard to watch progress.
- **Telegram Integration**: Remote control your dev loop. Receive notifications, pick tasks, and add new ones.
- **Persistence**: PostgreSQL database tracks every session, PR, and status change.
- **Dockerized**: Easy deployment with Docker Compose.

## 🛠 Architecture

1.  **`orchestrator.py`**: The "brain" that runs the loop, managing sessions and polling Jules.
2.  **`telegram_bot.py`**: The "remote control" that handles user commands and issue selection.
3.  **`dashboard.py`**: The "monitor" (Streamlit UI).
4.  **`db.py`**: Shared database layer (PostgreSQL).

## 📦 Setup

### 1. Prerequisites
- [Docker](https://www.docker.com/) and Docker Compose.
- A **GitHub Personal Access Token** (Classic with `repo` scope).
- A **Jules API Key**.
- An **OpenRouter API Key**.
- A **Telegram Bot Token**.

### 2. Configuration
Clone the repository and create your `.env` file:

```bash
cp .env.example .env
```

Fill in the required variables in `.env`:
- `GH_TOKEN`: Your GitHub PAT.
- `TARGET_REPO`: The `owner/repo` you want to automate.
- `ISSUE_LABEL`: The label Jules looks for (default: `jules-task`). **Important:** Jules only sees issues with this label.
- `JULES_API_KEY`: Your Google Jules API key.
- `OPENROUTER_API_KEY`: For backlog generation.
- `TELEGRAM_BOT_TOKEN`: Your bot token.
- `DB_PASSWORD`: Set a secure password for the local Postgres instance.

### 3. Launching
Use the provided `Makefile` for convenience:

```bash
make rebuild
```

Access the dashboard at `http://localhost:8501`.

## 🎮 Workflow

1.  **Start:** Run `make up`. The system starts **PAUSED** by default.
2.  **Resume:** Open your Telegram bot and click **▶️ Resume**.
3.  **Pick a Task:** The bot will list available open issues (with the `jules-task` label). Reply with `/pick <number>` to assign a task to Jules.
4.  **Coding:** Jules will work on the issue. You can monitor progress in the dashboard or via bot updates.
5.  **Review:** When finished, Jules creates a PR. The bot sends you the link.
6.  **Merge:** Review the PR on GitHub and merge it manually. The orchestrator will detect the merge and close the issue automatically.

## 🤖 Telegram Bot Commands

- `/start`: Show the main control panel.
- `/pick <number>`: Select an issue for Jules to work on.
- `/add_task Title:Body`: Create a new issue (automatically adds the `jules-task` label).
- `/status`: Show current system state and recent history.
- `/sync`: Manually trigger the LLM to generate new backlog items.

## 📄 License

MIT License. See [LICENSE](LICENSE) for details.