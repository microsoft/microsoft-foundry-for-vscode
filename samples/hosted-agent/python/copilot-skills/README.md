# Copilot SDK Skills Agent

This sample demonstrates how to build a hosted agent using the [GitHub Copilot SDK](https://www.npmjs.com/package/@anthropic-ai/sdk) with **skill directories**. Skills are declarative markdown files (`SKILL.md`) that define agent capabilities — the Copilot SDK automatically discovers and injects them into the session.

## Overview

| Component | Description |
|-----------|-------------|
| `main.py` | Entrypoint — discovers skill directories and starts the server |
| `agent.py` | `CopilotAgent` class — thin wrapper around `CopilotClient` for run/stream |
| `server.py` | Foundry protocol adapter — bridges `CopilotAgent` to the responses protocol |
| `_telemetry.py` | Azure Monitor / Application Insights setup |
| `greeting/` | Example skill — personalized greetings |
| `code-review/` | Example skill — code review with a checklist |

## Prerequisites

- Python 3.12+
- A [GitHub fine-grained PAT](https://github.com/settings/personal-access-tokens/new) with **Account permissions → Copilot Requests → Read-only**
- An [Azure AI Foundry project](https://ai.azure.com) (for deployment)

> **Note:** Classic tokens (`ghp_` prefix) are not supported by the Copilot SDK. You must use a fine-grained PAT (`github_pat_`), OAuth token (`gho_`), or GitHub App user token (`ghu_`).

## Getting Started

### 1. Configure environment

Copy `.env.sample` to `.env` and fill in the values:

```bash
cp .env.sample .env
```

```env
GITHUB_TOKEN=github_pat_...
AZURE_AI_PROJECT_ENDPOINT=https://your-project.services.ai.azure.com/api/projects/your-project-name
```

For deployment, set the token via the Azure Developer CLI so it's available as an environment variable in your hosted agent:

```bash
azd env set GITHUB_TOKEN <your-github-pat>
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run locally

```bash
python main.py
```

The agent starts on port **8088** by default (set `PORT` to override).

### 4. Deploy to Azure AI Foundry

Build and push the Docker image, then create a hosted agent using the `agent.manifest.yaml` manifest:

```bash
docker build -t copilot-skills-agent .
```

## How Skills Work

Any directory at the project root containing a `SKILL.md` file is automatically discovered as a skill when the agent starts. The `SKILL.md` describes the skill's capabilities and is injected into the Copilot session.

```
skills/
├── greeting/
│   └── SKILL.md       ← discovered as a skill
├── code-review/
│   ├── SKILL.md       ← discovered as a skill
│   └── references/
│       └── checklist.md
└── my-new-skill/
    └── SKILL.md       ← you add this
```

### Adding a skill

1. Create a new directory at the project root (e.g., `my-skill/`)
2. Add a `SKILL.md` file describing what the skill does
3. Restart the agent — it's picked up automatically

### Included examples

| Skill | Description |
|-------|-------------|
| `greeting/` | Responds to greeting requests with a personalized message |
| `code-review/` | Reviews code snippets and provides feedback using a checklist |

## Project Structure

```
skills/
│
│  SKILLS (add more here)
├── greeting/SKILL.md
├── code-review/SKILL.md
│
│  INFRASTRUCTURE
├── main.py                 # Entrypoint — skill discovery + create_agent()
├── agent.py                # CopilotAgent class (run/stream wrapper)
├── server.py               # Foundry protocol adapter
├── _telemetry.py           # Azure Monitor / App Insights setup
├── agent.manifest.yaml     # Agent metadata and env var declarations
├── Dockerfile              # Container build definition
├── requirements.txt        # Python dependencies
└── .env.sample             # Environment variable template
```

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `Failed to start GitHub Copilot client` | Invalid or expired token | Create a new fine-grained PAT with **Copilot Requests → Read-only** |
| `Telemetry setup skipped` | Missing or unreachable Azure project endpoint | Verify `AZURE_AI_PROJECT_ENDPOINT` is set and the project exists |
| `No skill directories discovered` | No `SKILL.md` files found at the project root | Ensure at least one subdirectory contains a `SKILL.md` file |
