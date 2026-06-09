#!/bin/bash
# setup-ssh.sh — Generate SSH key and copy to Proxmox for passwordless access
# Run this after install.sh
set -e

# ─────────────────────────────────────────
PROXMOX_IP="10.200.200.10"
PROXMOX_USER="root"
SSH_KEY_PATH="$HOME/.ssh/proxmox_id_ed25519"
# ─────────────────────────────────────────

echo "==> SSH Setup for Proxmox at $PROXMOX_IP"
echo ""

echo "==> Checking SSH key..."
if [ ! -f "$SSH_KEY_PATH" ]; then
  echo "    Generating new SSH key..."
  ssh-keygen -t ed25519 -f "$SSH_KEY_PATH" -N "" -C "proxmox-mcp-control"
else
  echo "    Key already exists at $SSH_KEY_PATH"
fi

echo "==> Copying public key to Proxmox (you'll be prompted for root password once)..."
ssh-copy-id -i "${SSH_KEY_PATH}.pub" "${PROXMOX_USER}@${PROXMOX_IP}"

echo "==> Testing passwordless connection..."
ssh -i "$SSH_KEY_PATH" -o StrictHostKeyChecking=accept-new \
  "${PROXMOX_USER}@${PROXMOX_IP}" \
  "echo '✓ SSH OK'; pveversion"

# Add convenience alias
if ! grep -q "alias proxmox=" ~/.bashrc 2>/dev/null; then
  echo "alias proxmox='ssh -i $SSH_KEY_PATH ${PROXMOX_USER}@${PROXMOX_IP}'" >> ~/.bashrc
  echo "==> Alias 'proxmox' added to ~/.bashrc — run: source ~/.bashrc"
fi

echo ""
echo "==> SSH setup complete."
echo "    Connect anytime with: ssh -i $SSH_KEY_PATH ${PROXMOX_USER}@${PROXMOX_IP}"
echo "    Or after sourcing .bashrc: proxmox"
