# Hosted Agent Samples

This folder contains sample templates for building code-based **hosted agents** that can be deployed to Microsoft Foundry. Templates are available in both **Python** and **.NET**.

## Available Templates

| Template | Python | .NET | Description |
|----------|--------|------|-------------|
| **Agent** | `python/agent` | `dotnet/agent` | A single agent with local tool execution (Seattle Hotel search demo) |
| **Workflow** | `python/workflow` | `dotnet/workflow` | A multi-agent workflow with Writer and Reviewer agents |
| **Minimal** | `python/minimal` | `dotnet/minimal` | A bare-bones Dockerfile for custom implementations |

## Placeholder Values

These samples are **project templates** and contain placeholder values that must be replaced before use:

- `{{AgentName}}` — Your agent's name
- `{{AZURE_AI_PROJECT_ENDPOINT}}` — Your Microsoft Foundry project endpoint (e.g., `https://<project>.services.ai.azure.com`)
- `{{AZURE_AI_MODEL_DEPLOYMENT_NAME}}` — Your deployed model name (e.g., `gpt-4o`, `gpt-4.1-mini`)
- `{{SafeProjectName}}` — (.NET) Your project name for the `.csproj` file

These placeholders appear in `agent.yaml`, source files, and project configuration files throughout the templates.

## Recommended: Use the Microsoft Foundry VS Code Extension

For the best experience creating hosted agents, we recommend using the **Microsoft Foundry for Visual Studio Code** extension instead of manually filling in placeholders. The extension provides a guided workflow that automatically configures your project, connects to your Microsoft Foundry resources, and scaffolds a ready-to-run agent project.

**Install the extension:** [Microsoft Foundry for Visual Studio Code](https://marketplace.visualstudio.com/items?itemName=ms-windows-ai-studio.windows-ai-studio)

With the extension you can:
- Scaffold a new hosted agent project with your settings pre-filled
- Deploy directly to Microsoft Foundry from VS Code
- Test and debug agents locally before deployment

## Project Structure

```
hosted-agent/
├── version-manifest.json      # Version and release metadata
├── python/
│   ├── agent/                 # Single agent with local tool
│   ├── workflow/              # Multi-agent workflow
│   └── minimal/               # Minimal Dockerfile only
└── dotnet/
    ├── agent/                 # Single agent with local tool
    ├── workflow/              # Multi-agent workflow
    └── minimal/               # Minimal Dockerfile only
```