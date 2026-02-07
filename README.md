# Octo-Jules 🐙

Octo-Jules is an autonomous development loop that leverages Google's **Jules API** to implement features and fixes directly from your GitHub Issues backlog. It automatically manages the lifecycle of a task from issue selection to PR creation and merging.

## 🚀 Features

- **Autonomous Orchestrator**: Fetches prioritized issues, triggers Jules coding sessions, and merges successful PRs.
- **Backlog Sustainer**: Uses LLMs (via OpenRouter) to analyze your codebase and automatically generate new, unique feature ideas when the backlog is low.
- **Real-time Monitoring**: Built-in Streamlit dashboard to watch Jules work in real-time.
- **Telegram Integration**: Remote control your dev loop. Receive notifications and add tasks directly from your phone.
- **Persistence**: SQLite database tracks every session, PR, and status change.
- **Dockerized**: Easy deployment to any VPS or local machine.

## 🛠 Architecture

1.  **`orchestrator.py`**: The "brain" that runs the infinite loop.
2.  **`backlog_sustainer.py`**: The "product manager" that keeps the work pipeline full.
3.  **`dashboard.py`**: The "monitor" (Streamlit UI).
4.  **`telegram_bot.py`**: The "remote control" active listener.

## 📦 Setup

### 1. Prerequisites
- [Docker](https://www.docker.com/) and Docker Compose.
- [GitHub CLI](https://cli.github.com/) (locally for initial setup).
- A **GitHub Personal Access Token** (Classic with `repo` scope or Fine-grained with Contents, Issues, and PRs write access).
- A **Jules API Key**.
- An **OpenRouter API Key**.

### 2. Configuration
Clone the repository and create your `.env` file:

```bash
cp .env.example .env
```

Fill in the required variables in `.env`:
- `GH_TOKEN`: Your GitHub PAT.
- `TARGET_REPO`: The `owner/repo` you want to automate.
- `JULES_API_KEY`: Your Google Jules API key.
- `OPENROUTER_API_KEY`: For backlog generation (Claude 3.5 Haiku recommended).
- `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID`: Optional, for remote control.

### 3. Launching
Use the provided `Makefile` for convenience:

```bash
make rebuild
```

Access the dashboard at `http://localhost:8501`.

## 🎮 Makefile Commands

- `make up`: Start all services.
- `make stop`: Stop all services.
- `make logs`: View all service logs.
- `make logs-orch`: View only the orchestrator logs.
- `make rebuild`: Rebuild images and restart.

## 🤖 Telegram Bot Commands

- `/status`: Show recent session history.
- `/add_task Title:Body`: Manually add a new task to the GitHub backlog.
- `/sync`: Manually trigger the LLM to generate new backlog items.

## 📄 License

MIT License. See [LICENSE](LICENSE) for details.
