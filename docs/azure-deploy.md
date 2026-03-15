# Deploying MigrationOps Copilot to Azure App Service

## Prerequisites

- Azure CLI installed and authenticated with `az login`
- An Azure subscription
- An Azure OpenAI resource with a deployed Responses model

## 1. Create a Resource Group

```bash
az group create --name migrationops-rg --location eastus
```

## 2. Create an App Service Plan

```bash
az appservice plan create \
  --name migrationops-plan \
  --resource-group migrationops-rg \
  --sku B1 \
  --is-linux
```

## 3. Create the Web App

```bash
az webapp create \
  --resource-group migrationops-rg \
  --plan migrationops-plan \
  --name migrationops-copilot-demo \
  --runtime "PYTHON:3.12"
```

## 4. Configure Application Settings

Use App Service settings for the Azure OpenAI connection details. For hackathon speed, API key auth is the simplest deployment path.

```bash
az webapp config appsettings set \
  --resource-group migrationops-rg \
  --name migrationops-copilot-demo \
  --settings \
  AZURE_OPENAI_ENDPOINT="https://example-resource.openai.azure.com" \
  AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME="gpt-4o-mini" \
  AZURE_OPENAI_API_KEY="replace-with-your-key"
```

For production, replace the API key with Key Vault plus managed identity.

## 5. Configure Startup Command

```bash
az webapp config set \
  --resource-group migrationops-rg \
  --name migrationops-copilot-demo \
  --startup-file "startup.sh"
```

## 6. Deploy The App

Deploy from the local workspace:

```bash
az webapp up \
  --name migrationops-copilot-demo \
  --resource-group migrationops-rg \
  --runtime "PYTHON:3.12"
```

Or connect App Service to the GitHub repository:

```bash
az webapp deployment source config \
  --name migrationops-copilot-demo \
  --resource-group migrationops-rg \
  --repo-url https://github.com/shahaman098/MigrationOps-Copilot \
  --branch main \
  --manual-integration
```

## 7. Verify

Open the deployed app in a browser:

```text
https://migrationops-copilot-demo.azurewebsites.net
```

Then run:

- a clean migration check: `https://google.com -> https://google.com`
- a broken migration check: `https://google.com -> https://expired.badssl.com`

## Deployment Notes

- The CLI path and web UI use the same pipeline code.
- The optional MCP path requires a separate MCP server process; the default App Service deployment uses direct discovery.
- Remediation actions remain simulated in both local and Azure deployments.
