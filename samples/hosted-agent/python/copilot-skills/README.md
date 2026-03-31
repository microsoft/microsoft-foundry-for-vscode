# Copilot Skills Agent (Code-Based)

A hosted agent template using `FoundryCBAgent` from the Azure AI AgentServer Core SDK. This template gives you direct control over streaming and non-streaming responses, making it ideal when you need fine-grained customization of the agent's behavior.

## How It Works

- **FoundryCBAgent**: Subclass the core `FoundryCBAgent` to implement `agent_run()` with full control over request handling and response construction.
- **OpenAI Responses API**: Uses `AIProjectClient` to obtain an OpenAI client and calls the Responses API for model inference.
- **Streaming Support**: Demonstrates manual construction of streaming events (`ResponseCreatedEvent`, `ResponseTextDeltaEvent`, etc.) for real-time token delivery.

## Prerequisites

- Python 3.12+
- An [Azure AI Foundry](https://ai.azure.com) project with a deployed model
- [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) (logged in via `az login`)

## Environment Variables

| Variable | Description |
|---|---|
| `AZURE_AI_PROJECT_ENDPOINT` | Your Azure AI Foundry project endpoint |
| `AZURE_AI_MODEL_DEPLOYMENT_NAME` | Model deployment name (default: `gpt-4.1-mini`) |

## Running Locally

1. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Linux/macOS
   .venv\Scripts\activate      # Windows
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Copy `.env` and fill in your values:
   ```bash
   cp .env .env.local
   ```

4. Run the agent:
   ```bash
   python main.py
   ```

   Or press **F5** in VS Code to launch with the debugger attached.

## Deploying to Microsoft Foundry

Deploy using the Azure Developer CLI:
```bash
azd up
```

Or deploy via the **Microsoft Foundry** VS Code extension.

## Additional Resources

- [Azure AI AgentServer Core SDK](https://pypi.org/project/azure-ai-agentserver-core/)
- [Azure AI Foundry Documentation](https://learn.microsoft.com/azure/ai-services/)
- [Managed Identities for Azure Resources](https://learn.microsoft.com/entra/identity/managed-identities-azure-resources/)
