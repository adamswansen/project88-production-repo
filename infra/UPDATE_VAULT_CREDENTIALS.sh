#!/bin/bash

# Project88Hub - Vault Credentials Update Script
# Updates Ansible vault files with new strong passwords and S3 configuration
# 
# SECURITY WARNING: Run this script in a secure environment
# Ensure you have the old vault password before running

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔐 Project88Hub Vault Credentials Update${NC}"
echo "=================================="
echo

# Verify we're in the correct directory
if [[ ! -d "ansible" ]]; then
    echo -e "${RED}❌ Error: Must run from infra/ directory${NC}"
    echo "Usage: cd infra/ && ./UPDATE_VAULT_CREDENTIALS.sh"
    exit 1
fi

cd ansible

# Check if vault files exist
if [[ ! -f "group_vars/prod_vault.yml" ]] || [[ ! -f "group_vars/dev_vault.yml" ]]; then
    echo -e "${RED}❌ Error: Vault files not found${NC}"
    echo "Expected: group_vars/prod_vault.yml and group_vars/dev_vault.yml"
    exit 1
fi

echo -e "${YELLOW}⚠️  SECURITY CHECKLIST:${NC}"
echo "1. ✅ Have you backed up the current vault files?"
echo "2. ✅ Do you have the current vault password?"
echo "3. ✅ Are you in a secure environment?"
echo "4. ✅ Do you have AWS S3 credentials ready?"
echo

read -p "Continue with vault update? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}🚫 Operation cancelled${NC}"
    exit 0
fi

# Define the new strong passwords
NEW_VAULT_PASSWORD="Pr0j3ct88-V4ult-S3cur3-2025!\$Hub"
PROD_DB_PASSWORD="P88-Pr0d-DB-S3cur3-2025!\$MySQL"
DEV_DB_PASSWORD="P88-D3v-DB-T3st-2025!\$MySQL"

echo -e "${BLUE}📝 Step 1: Creating new vault password file${NC}"
echo "$NEW_VAULT_PASSWORD" > .vault_pass_new
chmod 600 .vault_pass_new

echo -e "${BLUE}🔄 Step 2: Re-encrypting vault files with new password${NC}"

# Check if old vault password file exists
if [[ ! -f ".vault_pass" ]]; then
    echo -e "${YELLOW}⚠️  Old vault password file not found${NC}"
    echo "Please enter the current vault password manually when prompted"
    
    # Re-encrypt with manual password entry
    ansible-vault rekey group_vars/prod_vault.yml --new-vault-password-file .vault_pass_new
    ansible-vault rekey group_vars/dev_vault.yml --new-vault-password-file .vault_pass_new
else
    # Re-encrypt with existing password file
    ansible-vault rekey group_vars/prod_vault.yml --vault-password-file .vault_pass --new-vault-password-file .vault_pass_new
    ansible-vault rekey group_vars/dev_vault.yml --vault-password-file .vault_pass --new-vault-password-file .vault_pass_new
fi

echo -e "${GREEN}✅ Vault files re-encrypted successfully${NC}"

# Replace the vault password file
mv .vault_pass_new .vault_pass

echo -e "${BLUE}📝 Step 3: Updating vault content with new credentials${NC}"

# Create temporary unencrypted files for editing
echo -e "${YELLOW}📄 Decrypting production vault for editing...${NC}"
ansible-vault decrypt group_vars/prod_vault.yml --vault-password-file .vault_pass

echo -e "${YELLOW}📄 Decrypting development vault for editing...${NC}"
ansible-vault decrypt group_vars/dev_vault.yml --vault-password-file .vault_pass

# Update production vault content
echo -e "${BLUE}✏️  Updating production vault content${NC}"
cat > group_vars/prod_vault.yml << EOF
---
# Project88Hub Production Vault - Encrypted Credentials
# Generated: $(date)
# Updated with strong passwords and S3 configuration

# Database Credentials
vault_db_password: "$PROD_DB_PASSWORD"
vault_db_host: "localhost"
vault_db_port: 5432
vault_db_name: "project88_myappdb"
vault_db_user: "project88_myappuser"

# S3 Backup Configuration
vault_s3_bucket: "project88.bu"
vault_s3_region: "us-east-1"
vault_s3_access_key: "YOUR_AWS_ACCESS_KEY_ID"  # TODO: Replace with actual key
vault_s3_secret_key: "YOUR_AWS_SECRET_ACCESS_KEY"  # TODO: Replace with actual key

# Application Secrets
vault_jwt_secret: "P88-JWT-S3cr3t-Pr0d-2025!\$Token"
vault_flask_secret: "P88-Flask-S3cr3t-Pr0d-2025!\$Key"
vault_redis_password: "P88-R3dis-Pr0d-2025!\$Cache"

# SSL Configuration
vault_ssl_cert_email: "admin@project88hub.com"

# Backup Encryption
vault_backup_encryption_key: "P88-Backup-Encrypt-Pr0d-2025!\$Secure"

# Provider API Keys (if needed)
vault_runsignup_api_key: ""
vault_raceroster_api_key: ""
vault_haku_api_key: ""
vault_letsdothis_api_key: ""
EOF

# Update development vault content
echo -e "${BLUE}✏️  Updating development vault content${NC}"
cat > group_vars/dev_vault.yml << EOF
---
# Project88Hub Development Vault - Encrypted Credentials
# Generated: $(date)
# Updated with strong passwords and S3 configuration

# Database Credentials
vault_db_password: "$DEV_DB_PASSWORD"
vault_db_host: "localhost"
vault_db_port: 5433
vault_db_name: "project88_dev_myappdb"
vault_db_user: "project88_dev_user"

# S3 Backup Configuration (same bucket, different prefix)
vault_s3_bucket: "project88.bu"
vault_s3_region: "us-east-1"
vault_s3_access_key: "YOUR_AWS_ACCESS_KEY_ID"  # TODO: Replace with actual key
vault_s3_secret_key: "YOUR_AWS_SECRET_ACCESS_KEY"  # TODO: Replace with actual key

# Application Secrets (development versions)
vault_jwt_secret: "P88-JWT-S3cr3t-D3v-2025!\$Token"
vault_flask_secret: "P88-Flask-S3cr3t-D3v-2025!\$Key"
vault_redis_password: "P88-R3dis-D3v-2025!\$Cache"

# SSL Configuration
vault_ssl_cert_email: "admin@dev.project88hub.com"

# Backup Encryption
vault_backup_encryption_key: "P88-Backup-Encrypt-D3v-2025!\$Secure"

# Provider API Keys (development/testing)
vault_runsignup_api_key: ""
vault_raceroster_api_key: ""
vault_haku_api_key: ""
vault_letsdothis_api_key: ""
EOF

echo -e "${BLUE}🔒 Step 4: Re-encrypting vault files${NC}"

# Re-encrypt the vault files
ansible-vault encrypt group_vars/prod_vault.yml --vault-password-file .vault_pass
ansible-vault encrypt group_vars/dev_vault.yml --vault-password-file .vault_pass

echo -e "${GREEN}✅ Vault files updated and encrypted successfully${NC}"

echo -e "${BLUE}🧪 Step 5: Testing vault access${NC}"

# Test that we can decrypt the files
if ansible-vault view group_vars/prod_vault.yml --vault-password-file .vault_pass > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Production vault decryption test passed${NC}"
else
    echo -e "${RED}❌ Production vault decryption test failed${NC}"
    exit 1
fi

if ansible-vault view group_vars/dev_vault.yml --vault-password-file .vault_pass > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Development vault decryption test passed${NC}"
else
    echo -e "${RED}❌ Development vault decryption test failed${NC}"
    exit 1
fi

echo
echo -e "${GREEN}🎉 VAULT UPDATE COMPLETED SUCCESSFULLY!${NC}"
echo "=================================="
echo
echo -e "${YELLOW}📋 NEXT STEPS:${NC}"
echo "1. 🔐 Add new vault password to GitLab CI variables:"
echo "   Variable: ANSIBLE_VAULT_PASSWORD"
echo "   Value: $NEW_VAULT_PASSWORD"
echo
echo "2. ☁️  Update S3 credentials in vault files:"
echo "   ansible-vault edit group_vars/prod_vault.yml --vault-password-file .vault_pass"
echo "   ansible-vault edit group_vars/dev_vault.yml --vault-password-file .vault_pass"
echo
echo "3. 🔑 Generate and deploy SSH keys (see SSH_KEY_MANAGEMENT.md)"
echo
echo "4. 🧪 Test Ansible playbook connectivity:"
echo "   ansible-playbook playbooks/site.yml -i inventory/prod.ini --vault-password-file .vault_pass --check"
echo
echo -e "${RED}⚠️  SECURITY REMINDER:${NC}"
echo "- Securely store the new vault password"
echo "- Update GitLab CI variables"
echo "- Test all deployments before production use"
echo "- Remove any temporary credential files"
echo

# Clean up temporary files
if [[ -f ".vault_pass_new" ]]; then
    rm -f .vault_pass_new
fi

echo -e "${BLUE}🔐 Vault update completed successfully!${NC}"