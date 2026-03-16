# Deploying MigrationOps Copilot to Azure App Service

This repo supports two Azure runtime modes:

1. Direct Azure OpenAI: the app uses `AZURE_OPENAI_ENDPOINT` and `AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME`.
2. Azure AI project endpoint / Foundry-compatible mode: the app uses `AZURE_AI_PROJECT_ENDPOINT` and `AZURE_AI_MODEL_DEPLOYMENT_NAME`.

The hosted MCP path is optional. When `MCP_SERVER_URL` is set to a public HTTPS endpoint and `AZURE_AI_PROJECT_ENDPOINT` is configured, the Discovery agent uses the hosted MCP tool path so Azure executes the MCP calls remotely.

## Prerequisites

- Azure CLI installed and authenticated with `az login`
- Contributor or equivalent write access to the target Azure resource group
- An Azure OpenAI deployment or an Azure AI project-compatible `services.ai.azure.com` endpoint
- For hosted MCP: a second App Service instance to run `startup-mcp.sh`

## 1. Create the Resource Group

```bash
az group create --name migrationops-rg --location eastus2
```

## 2. Create the App Service Plan

```bash
az appservice plan create \
  --name migrationops-plan \
  --resource-group migrationops-rg \
  --sku B1 \
  --is-linux
```

## 3. Create the Main Web App

```bash
az webapp create \
  --resource-group migrationops-rg \
  --plan migrationops-plan \
  --name migrationops-copilot-demo \
  --runtime "PYTHON:3.12"
```

## 4. Configure the Main App Settings

### Option A: Direct Azure OpenAI

```bash
az webapp config appsettings set \
  --resource-group migrationops-rg \
  --name migrationops-copilot-demo \
  --settings \
  AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com" \
  AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME="gpt-4o-mini"
```

If the app should use API key auth instead of Azure identity:

```bash
az webapp config appsettings set \
  --resource-group migrationops-rg \
  --name migrationops-copilot-demo \
  --settings \
  AZURE_OPENAI_API_KEY="replace-with-your-key"
```

### Option B: Azure AI project endpoint / Foundry-compatible path

```bash
az webapp config appsettings set \
  --resource-group migrationops-rg \
  --name migrationops-copilot-demo \
  --settings \
  AZURE_AI_PROJECT_ENDPOINT="https://your-resource.services.ai.azure.com/" \
  AZURE_AI_MODEL_DEPLOYMENT_NAME="gpt-5-mini"
```

The app uses `DefaultAzureCredential`, so App Service managed identity works in Azure and Azure CLI auth works locally.

## 5. Optional: Enable Managed Identity For the Main App

```bash
az webapp identity assign \
  --resource-group migrationops-rg \
  --name migrationops-copilot-demo
```

Grant the managed identity access to the Azure OpenAI or Azure AI project resource according to your organization's RBAC policy.

## 6. Optional: Create the Hosted MCP Web App

Create a second web app from the same repo if you want Azure to call the MCP server remotely.

```bash
az webapp create \
  --resource-group migrationops-rg \
  --plan migrationops-plan \
  --name migrationops-copilot-mcp \
  --runtime "PYTHON:3.12"
```

Configure the MCP app to run the dedicated startup script:

```bash
az webapp config set \
  --resource-group migrationops-rg \
  --name migrationops-copilot-mcp \
  --startup-file "startup-mcp.sh"
```

The MCP app serves its tools at:

```text
https://migrationops-copilot-mcp.azurewebsites.net/mcp
```

Then point the main app at that endpoint:

```bash
az webapp config appsettings set \
  --resource-group migrationops-rg \
  --name migrationops-copilot-demo \
  --settings \
  MCP_SERVER_URL="https://migrationops-copilot-mcp.azurewebsites.net/mcp"
```

## 7. Configure the Main App Startup Command

```bash
az webapp config set \
  --resource-group migrationops-rg \
  --name migrationops-copilot-demo \
  --startup-file "startup.sh"
```

## 8. Deploy the Code

Deploy from the local workspace:

```bash
az webapp up \
  --name migrationops-copilot-demo \
  --resource-group migrationops-rg \
  --plan migrationops-plan \
  --runtime "PYTHON:3.12"
```

For the hosted MCP app, run the same command with the MCP app name after configuring its startup file:

```bash
az webapp up \
  --name migrationops-copilot-mcp \
  --resource-group migrationops-rg \
  --plan migrationops-plan \
  --runtime "PYTHON:3.12"
```

## 9. Verify

Open the deployed main app:

```text
https://migrationops-copilot-demo.azurewebsites.net
```

Then verify:

- direct mode: `https://google.com -> https://google.com`
- broken migration mode: `https://google.com -> https://expired.badssl.com`
- optional hosted MCP mode: enable MCP in the UI or run `python main.py ... --mcp` with `MCP_SERVER_URL` set to the public MCP app URL

## Notes

- Live Azure deployment is supported by the repo, but it requires Azure write access to create resource groups, App Service plans, and web apps.
- The web UI and CLI both use the same pipeline code.
- The hosted MCP path requires a public HTTPS MCP endpoint.
- Remediation actions remain simulated in both local and Azure deployments.
