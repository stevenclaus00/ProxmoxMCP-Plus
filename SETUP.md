# Quick Setup Guide
## ProxmoxMCP-Plus — Steven Claus / MendoAI

This fork adds a one-shot installer and SSH setup script on top of ProxmoxMCP-Plus.
Anyone can clone this repo and be controlling Proxmox via MCP in under 5 minutes.

---

## Prerequisites

- Ubuntu/Debian or WSL on Windows
- `curl` and `git` installed
- Proxmox server running at `10.200.200.10` (or edit the scripts)
- A Proxmox API token (see below)

---

## Step 1 — Create a Proxmox API Token

1. Log into Proxmox web UI → `Datacenter > Permissions > API Tokens`
2. Click **Add**
3. User: `root@pam`, Token ID: `mcp-token`
4. Uncheck **Privilege Separation** for full access
5. Save — copy both the token name and token value

---

## Step 2 — Clone & Install

```bash
git clone https://github.com/stevenclaus00/ProxmoxMCP-Plus.git
cd ProxmoxMCP-Plus
chmod +x install.sh setup-ssh.sh
./install.sh
```

You'll be prompted for your Proxmox user, token name, and token value.

---

## Step 3 — Set Up SSH (Optional but Recommended)

For direct SSH access and container command execution:

```bash
./setup-ssh.sh
```

You'll enter the Proxmox root password once — after that it's passwordless.

---

## Step 4 — Connect Your AI Client

### AntiGravity / Cursor / VS Code

Add to your MCP config:

```json
{
  "mcpServers": {
    "proxmox-mcp-plus": {
      "command": "uvx",
      "args": ["proxmox-mcp-plus"],
      "env": {
        "PROXMOX_HOST": "10.200.200.10",
        "PROXMOX_USER": "root@pam",
        "PROXMOX_TOKEN_NAME": "mcp-token",
        "PROXMOX_TOKEN_VALUE": "your-token-secret",
        "PROXMOX_PORT": "8006",
        "PROXMOX_VERIFY_SSL": "false"
      }
    }
  }
}
```

### Gemini CLI (fallback)

```bash
gemini --mcp proxmox-config/mcp-config.json
```

---

## What You Can Do Once Connected

- Create, start, stop, delete VMs and LXCs
- Snapshot and rollback VMs
- Download ISOs
- Execute commands inside containers
- Track long-running async jobs
- Monitor cluster health and storage

---

## Proxmox Server
- IP: `10.200.200.10`
- Port: `8006`
- Default user: `root@pam`
