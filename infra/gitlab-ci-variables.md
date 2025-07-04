# GitLab CI/CD Variables Configuration

This document outlines the required GitLab CI/CD variables for the Project88Hub deployment pipeline.

## **Required Variables (Settings > CI/CD > Variables)**

### **SSH & Server Access**
```
SSH_PRIVATE_KEY_PROD (Protected, Masked)
- Type: File or Variable
- Value: Production SSH private key for accessing production VPS (69.62.69.90)
- Used by: Production deployment jobs

SSH_PRIVATE_KEY_DEV (Protected, Masked)
- Type: File or Variable
- Value: Development SSH private key for accessing development VPS
- Used by: Development deployment jobs

DEV_VPS_IP (Protected)
- Type: Variable  
- Value: Development VPS IP address (when available)
- Used by: Development deployment and integration tests
```

### **Ansible Configuration**
```
ANSIBLE_VAULT_PASSWORD (Protected, Masked)
- Type: Variable
- Value: Pr0j3ct88-V4ult-S3cur3-2025!$Hub
- Used by: All Ansible deployment jobs
```

### **Container Registry (Auto-configured by GitLab)**
```
CI_REGISTRY_IMAGE (Automatic)
CI_REGISTRY_USER (Automatic) 
CI_REGISTRY_PASSWORD (Automatic)
- Auto-populated by GitLab for container registry access
```

## **Optional Variables**

### **Notifications**
```
SLACK_WEBHOOK_URL (Protected)
- Type: Variable
- Value: Slack webhook for deployment notifications
- Used by: Notification jobs

NOTIFICATION_EMAIL (Protected)
- Type: Variable  
- Value: alex@superracesystems.com,adam@brrm.com
- Used by: Email alerts
```

### **External Services**
```
SMTP_SERVER (Protected)
- Type: Variable
- Value: SMTP server for application emails
- Used by: Authentication service

STRIPE_WEBHOOK_SECRET (Protected, Masked)
- Type: Variable
- Value: Stripe webhook secret for payment processing
- Used by: Authentication service builds
```

## **Pipeline Behavior**

### **Branch Rules:**
- `main` branch → Manual production deployment
- `dev` branch → Automatic development deployment  
- Feature branches → Lint and test only
- All branches → Security scanning

### **Manual Deployment Jobs:**
Both deployment jobs are set to `when: manual` for safety:
- Development deployment requires manual trigger
- Production deployment requires manual approval

### **Environment URLs:**
- Development: `http://$DEV_VPS_IP:5002` (when dev VPS available)
- Production: `https://display.project88hub.com`

## **Setup Instructions**

1. **Add SSH Keys (Separate for Production and Development):**
   ```bash
   # Generate SSH key pairs for CI/CD (see SSH_KEY_MANAGEMENT.md for details)
   ssh-keygen -t rsa -b 4096 -C "gitlab-ci-prod@project88hub.com" -f ~/.ssh/project88-prod-gitlab-ci
   ssh-keygen -t rsa -b 4096 -C "gitlab-ci-dev@project88hub.com" -f ~/.ssh/project88-dev-gitlab-ci
   
   # Add public keys to respective VPS servers
   ssh-copy-id -i ~/.ssh/project88-prod-gitlab-ci.pub appuser@69.62.69.90
   ssh-copy-id -i ~/.ssh/project88-dev-gitlab-ci.pub appuser@$DEV_VPS_IP
   
   # Add private keys to GitLab CI/CD variables
   cat ~/.ssh/project88-prod-gitlab-ci  # Copy to SSH_PRIVATE_KEY_PROD variable
   cat ~/.ssh/project88-dev-gitlab-ci   # Copy to SSH_PRIVATE_KEY_DEV variable
   ```

2. **Configure Ansible Vault:**
   ```bash
   # Add vault password to GitLab CI/CD variables
   # Variable name: ANSIBLE_VAULT_PASSWORD
   # Value: Pr0j3ct88-V4ult-S3cur3-2025!$Hub
   ```

3. **Configure AWS S3 Backup Credentials:**
   ```bash
   # Add S3 credentials to Ansible vault files (see VAULT_SETUP_INSTRUCTIONS.md)
   # Edit production vault:
   ansible-vault edit infra/ansible/group_vars/prod_vault.yml --vault-password-file .vault_pass
   
   # Add these values:
   # vault_s3_access_key: "YOUR_AWS_ACCESS_KEY_ID"
   # vault_s3_secret_key: "YOUR_AWS_SECRET_ACCESS_KEY"
   # vault_s3_bucket: "project88.bu"
   # vault_s3_region: "us-east-1"
   ```

4. **Update Development IP:**
   ```bash
   # When dev VPS is ready, update GitLab CI/CD variable:
   # Variable name: DEV_VPS_IP  
   # Value: [actual dev VPS IP]
   ```

## **Security Notes**

- All sensitive variables are marked as **Protected** (only available on protected branches)
- Passwords and keys are marked as **Masked** (hidden in logs)
- SSH keys use RSA 4096-bit encryption
- Ansible vault files use AES256 encryption
- Container images are scanned for vulnerabilities

## **Pipeline Monitoring**

The pipeline includes comprehensive health checks:
- Container health status verification
- Service port availability testing  
- Database connectivity validation
- Application endpoint testing
- Resource utilization monitoring

## **Troubleshooting**

### **Common Issues:**

1. **SSH Connection Failed:**
   - Verify SSH_PRIVATE_KEY is correct
   - Ensure public key is added to target servers
   - Check server IP addresses

2. **Ansible Vault Decryption Failed:**
   - Verify ANSIBLE_VAULT_PASSWORD is correct
   - Check vault files are properly encrypted

3. **Container Registry Push Failed:**
   - Verify GitLab container registry is enabled
   - Check CI_REGISTRY_* variables are populated

4. **Development Deployment Skipped:**
   - Ensure DEV_VPS_IP variable is set
   - Verify development server is accessible