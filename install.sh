#!/bin/bash
# install.sh — One-shot installer for ProxmoxMCP-Plus
# Clones the repo, sets up the venv, configures Proxmox credentials, and starts the server.
# Works on Ubuntu/Debian and WSL.
set -e

# ─────────────────────────────────────────
# EDIT THESE BEFORE RUNNING (or leave blank to be prompted)
PROXMOX_HOST="10.200.200.10"
PROXMOX_PORT="8006"
PROXMOX_USER=""          # e.g. root@pam
PROXMOX_TOKEN_NAME=""    # e.g. mcp-token
PROXMOX_TOKEN_VALUE=""   # your token secret
PROXMOX_VERIFY_SSL="false"
# ─────────────────────────────────────────

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==> ProxmoxMCP-Plus Installer"
echo "    Repo: $REPO_DIR"
echo ""

# Prompt for any missing values
if [ -z "$PROXMOX_USER" ]; then
  read -rp "Proxmox user (e.g. root@pam): " PROXMOX_USER
fi
if [ -z "$PROXMOX_TOKEN_NAME" ]; then
  read -rp "API token name (e.g. mcp-token): " PROXMOX_TOKEN_NAME
fi
if [ -z "$PROXMOX_TOKEN_VALUE" ]; then
  read -rsp "API token value (hidden): " PROXMOX_TOKEN_VALUE
  echo ""
fi

echo ""
echo "==> Installing uv if not present..."
if ! command -v uv &>/dev/null; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  source "$HOME/.local/bin/env" 2>/dev/null || export PATH="$HOME/.local/bin:$PATH"
fi

echo "==> Setting up Python virtual environment..."
cd "$REPO_DIR"
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"

echo "==> Writing proxmox-config/config.json..."
mkdir -p proxmox-config
cat > proxmox-config/config.json << EOF
{
  "proxmox": {
    "host": "${PROXMOX_HOST}",
    "port": ${PROXMOX_PORT},
    "verify_ssl": ${PROXMOX_VERIFY_SSL},
    "service": "PVE"
  },
  "auth": {
    "user": "${PROXMOX_USER}",
    "token_name": "${PROXMOX_TOKEN_NAME}",
    "token_value": "${PROXMOX_TOKEN_VALUE}"
  },
  "logging": {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file": "proxmox_mcp.log"
  },
  "jobs": {
    "sqlite_path": "proxmox-jobs.sqlite3"
  }
}
EOF

echo "==> Config written to proxmox-config/config.json"
echo ""
echo "==> Installation complete."
echo ""
echo "    To start the MCP server:"
echo "    source .venv/bin/activate && PROXMOX_MCP_CONFIG=proxmox-config/config.json python main.py"
echo ""
echo "    Or use uvx directly (no clone needed, for clients):"
echo "    uvx proxmox-mcp-plus"
echo ""
echo "    Next: run ./setup-ssh.sh to set up passwordless SSH to Proxmox."
