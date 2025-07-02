#!/bin/bash
# Script to update development VPS IP when it becomes available

set -e

if [ $# -ne 1 ]; then
    echo "Usage: $0 <dev_vps_ip>"
    echo "Example: $0 192.168.1.100"
    exit 1
fi

DEV_VPS_IP="$1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INVENTORY_FILE="$SCRIPT_DIR/ansible/inventory/dev.ini"

echo "🔧 Updating development VPS IP to: $DEV_VPS_IP"

# Validate IP format
if ! [[ $DEV_VPS_IP =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
    echo "❌ Invalid IP address format: $DEV_VPS_IP"
    exit 1
fi

# Backup current inventory file
cp "$INVENTORY_FILE" "$INVENTORY_FILE.backup.$(date +%Y%m%d_%H%M%S)"
echo "✅ Backed up inventory file"

# Update the inventory file
sed -i "s/DEV_VPS_IP_PLACEHOLDER/$DEV_VPS_IP/g" "$INVENTORY_FILE"
echo "✅ Updated inventory file: $INVENTORY_FILE"

# Test SSH connectivity
echo "🔍 Testing SSH connectivity to dev VPS..."
if ssh -o ConnectTimeout=10 -o BatchMode=yes appuser@$DEV_VPS_IP exit 2>/dev/null; then
    echo "✅ SSH connectivity successful"
else
    echo "⚠️  SSH connectivity test failed - please verify:"
    echo "   1. VPS is running and accessible"
    echo "   2. SSH key is properly configured"
    echo "   3. User 'appuser' exists on the target system"
fi

# Update GitLab CI/CD variable (if gitlab-cli is available)
if command -v glab &> /dev/null; then
    echo "🔧 Updating GitLab CI/CD variable..."
    glab variable set DEV_VPS_IP "$DEV_VPS_IP" --scope project || echo "⚠️  Please manually update DEV_VPS_IP variable in GitLab"
else
    echo "⚠️  GitLab CLI not found. Please manually update CI/CD variable:"
    echo "   Variable: DEV_VPS_IP"
    echo "   Value: $DEV_VPS_IP"
fi

echo ""
echo "🎉 Development VPS IP update complete!"
echo ""
echo "Next steps:"
echo "1. Verify GitLab CI/CD variable DEV_VPS_IP is set to: $DEV_VPS_IP"
echo "2. Test deployment: git push origin dev"
echo "3. Monitor pipeline: https://gitlab.com/your-project/-/pipelines"
echo ""
echo "Test Ansible connectivity:"
echo "cd $SCRIPT_DIR/ansible"
echo "ansible dev -i inventory/dev.ini -m ping"