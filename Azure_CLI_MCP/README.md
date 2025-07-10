# Azure CLI Chat Assistant

A modern web-based chat interface for Azure CLI operations, built with TypeScript, Flask, and Model Context Protocol (MCP).

## Features

- 🤖 **Natural Language Interface**: Chat with your Azure resources using plain English
- 🎨 **Modern UI**: Beautiful, responsive chat interface with dark mode support
- ⚡ **Real-time**: Instant feedback and connection status indicators
- 🔒 **Type Safe**: Built with TypeScript for robust error handling
- 🚀 **Fast**: Optimized performance with async operations
- 📱 **Responsive**: Works perfectly on desktop, tablet, and mobile

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Flask Server   │    │   MCP Client    │
│   (TypeScript)  │◄──►│   (Python)       │◄──►│   (Azure CLI)   │
│                 │    │                  │    │                 │
│ • Chat UI       │    │ • API Endpoints  │    │ • Azure Tools   │
│ • Type Safety   │    │ • Session Mgmt   │    │ • Command Exec  │
│ • Real-time     │    │ • Error Handling │    │ • Auth Handling │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Prerequisites

1. **Node.js** (v16+): For TypeScript compilation
2. **Python** (3.8+): For the Flask server and MCP client
3. **Azure CLI**: Must be installed and configured
4. **Docker** (optional): For containerized Azure CLI execution

## Installation

### 1. Clone and Setup

```bash
git clone <your-repo>
cd azure-cli-chat-assistant

# Install Python dependencies
pip install -r requirements.txt

# Install Node.js dependencies
npm install
```

### 2. Environment Configuration

Create a `.env` file in the project root:

```env
# Azure Credentials (if using service principal)
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
AZURE_SUBSCRIPTION_ID=your-subscription-id

# Or use this format for Docker mode
AZURE_CREDENTIALS={"clientId": "your-client-id", "clientSecret": "your-client-secret", "subscriptionId": "your-subscription-id", "tenantId": "your-tenant-id", "activeDirectoryEndpointUrl": "https://login.microsoftonline.com", "resourceManagerEndpointUrl": "https://management.azure.com/", "activeDirectoryGraphResourceId": "https://graph.windows.net/", "sqlManagementEndpointUrl": "https://management.core.windows.net:8443/", "galleryEndpointUrl": "https://gallery.azure.com/", "managementEndpointUrl": "https://management.core.windows.net/"}

# Optional: Server configuration
PORT=5000
DEBUG=false
```

### 3. Azure CLI Setup

Make sure Azure CLI is installed and you're logged in:

```bash
# Install Azure CLI (if not already installed)
# Windows: winget install Microsoft.AzureCLI
# macOS: brew install azure-cli
# Linux: curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Login to Azure
az login

# Verify your setup
az account show
```

## Quick Start

### Option 1: Use the Build Script (Recommended)

```bash
# Build and start everything
python build.py

# Or just build without starting
python build.py --build-only
```

### Option 2: Manual Build

```bash
# Compile TypeScript
npm run build

# Start the server
python app.py
```

### Option 3: Development Mode

```bash
# Terminal 1: Watch TypeScript changes
npm run watch

# Terminal 2: Start Flask server
python app.py
```

## Usage

1. **Open your browser** to `http://localhost:5000`
2. **Wait for connection** - The status indicator will turn green when ready
3. **Start chatting** - Try these examples:
   - "List all my resource groups"
   - "Show me my storage accounts"
   - "What virtual machines do I have?"
   - "Create a new resource group called test-rg"

### Keyboard Shortcuts

- `Enter` - Send message
- `Shift + Enter` - New line
- `Ctrl/Cmd + K` - Clear chat
- `Escape` - Focus input field

## API Endpoints

### Chat Endpoint
```http
POST /api/chat
Content-Type: application/json

{
  "message": "List my resource groups",
  "conversation_id": "optional-uuid"
}
```

### Health Check
```http
GET /health
```

### Status Information
```http
GET /api/status
```

## Project Structure

```
azure-cli-chat-assistant/
├── src/                    # TypeScript source files
│   ├── types.ts           # Type definitions
│   ├── chat-manager.ts    # Chat logic
│   └── app.ts            # Main application
├── static/                # Web assets
│   ├── index.html        # Main HTML file
│   ├── styles.css        # Styles
│   └── dist/             # Compiled TypeScript
├── main.py               # MCP client implementation
├── server.py             # Azure CLI MCP server
├── app.py                # Flask web server
├── build.py              # Build script
├── package.json          # Node.js dependencies
├── tsconfig.json         # TypeScript configuration
└── requirements.txt      # Python dependencies
```

## Development

### TypeScript Development

The frontend is built with modern TypeScript featuring:

- **Strict Type Checking**: Full type safety with strict mode enabled
- **Modern ES Modules**: Clean import/export syntax
- **DOM Type Safety**: Proper typing for DOM interactions
- **Error Boundaries**: Graceful error handling throughout

### Adding New Features

1. **Frontend Changes**: Edit files in `src/`
2. **Backend Changes**: Edit `app.py` or `main.py`
3. **Styling**: Update `static/styles.css`
4. **Build**: Run `npm run build` or use the watch mode

### Debugging

Enable debug mode by setting `DEBUG=true` in your `.env` file or:

```bash
DEBUG=true python app.py
```

This will enable:
- Detailed logging
- Flask debug mode
- Source map support for TypeScript

## Troubleshooting

### Common Issues

**1. TypeScript compilation errors**
```bash
# Clean build
rm -rf static/dist node_modules
npm install
npm run build
```

**2. Azure CLI connection issues**
```bash
# Check Azure CLI status
az account show

# Re-authenticate
az login

# Check Docker (if using Docker mode)
docker --version
```

**3. Python import errors**
```bash
# Reinstall dependencies
pip install -r requirements.txt

# Check Python version
python --version  # Should be 3.8+
```

**4. Port already in use**
```bash
# Use a different port
PORT=8080 python app.py
```

### Getting Help

1. Check the browser console for frontend errors
2. Check the terminal output for backend errors
3. Verify your Azure CLI setup with `az account show`
4. Ensure all dependencies are installed correctly

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `npm run lint && python -m pytest`
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

---

**Built with ❤️ using TypeScript, Flask, and Azure CLI** 