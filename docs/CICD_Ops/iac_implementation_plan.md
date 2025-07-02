# Infrastructure-as-Code Implementation Plan - Project88

File: `iac_implementation_plan.md`  
Version: **v1.0 – 2025-07-02**  
Maintainer: DevOps Team  
Status: **Ready for Implementation**

---

## 📋 **Project Overview**

Complete IaC implementation for Project88Hub dual-environment setup:
- **Production VPS**: 69.62.69.90 (8 CPU, 32GB RAM, 400GB disk)
- **Development VPS**: TBD (2 CPU, 8GB RAM, 100GB disk)
- **Platform**: Hostinger KVM with AlmaLinux 9.6

---

## 🎯 **Implementation Scope**

### **Infrastructure Components**
- **4 Applications**: Race Display, ChronoTrack Collector, AI Platform, Authentication
- **Database Strategy**: Separate PostgreSQL per environment, dev with trimmed data
- **Backup Strategy**: S3-based with nightly dev refresh
- **Domain Structure**: `dev.*.project88hub.com` pattern
- **CI/CD**: GitLab Premium with branch-based deployments

### **Branch Strategy (Confirmed)**
```
main branch    → Manual deploy to Production VPS
dev branch     → Auto deploy to Development VPS
feature/*      → Lint/test only (no deployment)
hotfix/*       → Optional direct production deployment
```

---

## 📅 **10-Day Implementation Timeline**

## **Phase 1: Foundation Setup (Days 1-3)**

### **Day 1: Environment Configuration**
**Deliverables:**
- Complete inventory files with server specifications
- Group variables with environment-specific configurations
- Ansible Vault setup for secrets management

**Tasks:**
```bash
# Inventory Configuration
infra/ansible/inventory/prod.ini:
[prod]
prod-vps ansible_host=69.62.69.90 ansible_user=appuser

infra/ansible/inventory/dev.ini:
[dev]
dev-vps ansible_host=<DEV_VPS_IP> ansible_user=appuser

# Domain Structure
Production: project88hub.com, display.project88hub.com, ai.project88hub.com
Development: dev.project88hub.com, dev.display.project88hub.com, dev.ai.project88hub.com
```

**Environment Variables:**
- Database: `project88_myappdb` (prod), `project88_dev_myappdb` (dev)
- Ports: Race Display (5001 prod, 5002 dev), AI Platform (8501 prod, 8502 dev)
- ChronoTrack: Port 61611 (both environments)

### **Day 2: Core Ansible Roles**
**roles/common:**
- User management and SSH hardening
- UFW firewall configuration
- Fail2ban security
- AlmaLinux 9.6 system optimization

**roles/docker:**
- Docker Engine installation
- Docker Compose plugin
- Container registry authentication

**Key Security Features:**
- Separate system users per environment
- Port isolation and firewall rules
- SSL certificate management (Let's Encrypt)

### **Day 3: Application Deployment Role**
**roles/project88:**
- All 4 application deployments
- Environment-specific configurations
- Service health checks
- Redis isolation (separate instances)

**roles/backup:**
- S3 backup implementation
- Nightly dev database refresh (last 500 records strategy)
- Automated cleanup and retention

---

## **Phase 2: CI/CD Pipeline Implementation (Days 4-6)**

### **Day 4: GitLab CI Configuration**
**File:** `infra/gitlab-ci.yml` (populate existing empty file)

**Pipeline Structure:**
```yaml
stages: [lint, build, test, security, deploy_dev, integration, deploy_prod]

variables:
  DOCKER_TLS_CERTDIR: ""
  IMAGE_REPO: $CI_REGISTRY_IMAGE
  IMAGE_TAG: $CI_COMMIT_SHA

# Security Scans (GitLab Premium)
include:
  - template: SAST.gitlab-ci.yml
  - template: Dependency-Scanning.gitlab-ci.yml
  - template: Container-Scanning.gitlab-ci.yml
  - template: Secret-Detection.gitlab-ci.yml
  - template: License-Scanning.gitlab-ci.yml
```

**Branch Deployment Logic:**
- `dev` branch → Auto deploy to dev VPS
- `main` branch → Manual approval for prod deployment
- Feature branches → Lint and test only

### **Day 5: Security & Secrets Management**
**Ansible Vault Configuration:**
```yaml
# group_vars/prod/vault.yml (encrypted)
vault_db_password: "production_secure_password"
vault_s3_access_key: "AWS_ACCESS_KEY"
vault_s3_secret_key: "AWS_SECRET_KEY"

# group_vars/dev/vault.yml (encrypted)  
vault_db_password: "development_secure_password"
vault_s3_access_key: "AWS_ACCESS_KEY"
vault_s3_secret_key: "AWS_SECRET_KEY"
```

**GitLab CI Variables:**
- `ANSIBLE_SSH_KEY` (protected)
- `ANSIBLE_VAULT_PASSWORD` (protected)
- `CI_REGISTRY_USER/PASSWORD` (protected)

### **Day 6: Database Management Strategy**
**Dev Database Refresh Logic:**
```sql
-- Nightly refresh strategy (last 500 records)
-- Keep full structure, trim data selectively
CREATE TABLE dev_refresh_strategy AS
SELECT 
  'events' as table_name,
  'last 500 by date' as strategy,
  'SELECT * FROM events ORDER BY created_at DESC LIMIT 500' as query;
```

**Tables to Keep Full in Dev:**
- `timing_partners` (multi-tenant structure)
- `users` (authentication testing)
- `providers` (integration testing)

**Tables to Trim:**
- `ct_events`, `ct_participants`, `ct_results` (last 500 records)
- `runsignup_events`, `runsignup_participants` (recent data only)

---

## **Phase 3: Monitoring & Validation (Days 7-10)**

### **Day 7-8: Health Monitoring Implementation**
**Email Alert Configuration:**
- Recipients: alex@superracesystems.com, adam@brrm.com
- Triggers: Service failures, disk space >80%, memory >85%
- Frequency: Immediate for critical, daily digest for warnings

**Service Health Checks:**
```yaml
# Health check endpoints
- name: Race Display Health
  uri: "https://{{ domain_prefix }}.display.project88hub.com/health"
  
- name: AI Platform Health  
  uri: "https://{{ domain_prefix }}.ai.project88hub.com/health"
  
- name: ChronoTrack Collector
  uri: "http://localhost:61612/status"
```

### **Day 9: Integration Testing**
**End-to-End Pipeline Testing:**
- Dev deployment validation
- Database connectivity testing
- Application integration verification
- SSL certificate validation
- Backup/restore procedures

**Rolling Deployment Testing:**
- Zero-downtime deployment validation
- Rollback procedure testing
- Health check integration
- Multi-application coordination

### **Day 10: Production Readiness**
**Production Deployment Validation:**
- Manual deployment approval workflow
- Production environment health verification
- Monitoring alert testing
- Documentation completion

---

## 🔧 **Technical Implementation Details**

### **Database Strategy**
```yaml
# Production Database
database:
  host: localhost
  name: project88_myappdb
  user: project88_myappuser
  retention: full_production_data
  
# Development Database  
database_dev:
  host: localhost
  name: project88_dev_myappdb
  user: project88_dev_user
  refresh_schedule: "0 3 * * *"  # 3 AM daily
  data_strategy: last_500_records
```

### **S3 Backup Configuration**
```yaml
backup:
  provider: s3
  bucket: s3://p88-backup-project88hub
  regions: us-east-1
  retention:
    daily: 14
    weekly: 8
    monthly: 12
  schedule:
    production: "0 2 * * *"  # 2 AM daily
    development: "0 4 * * *"  # 4 AM daily (after refresh)
```

### **Application Port Allocation**
| Service | Production | Development |
|---------|------------|-------------|
| Race Display | 5001 | 5002 |
| AI Platform | 8501 | 8502 |
| ChronoTrack Collector | 61611 | 61611 |
| Authentication | 8000 | 8001 |
| Redis | 6379 | 6380 |
| PostgreSQL | 5432 | 5433 |

---

## 🚨 **Critical Questions for Final Implementation**

### **Infrastructure Questions**
1. **Dev VPS IP Address**: What will be the IP address when dev VPS is provisioned?
2. **S3 Bucket Setup**: Do you have AWS credentials, or should Ansible create the bucket?
3. **SSL Certificate**: Should we set up automatic Let's Encrypt renewal for both environments?

### **Database Questions**
4. **Data Trimming Strategy**: For "last 500 records" - should this be:
   - Last 500 events with all their participants?
   - Last 500 participants across all events?
   - Last 500 records from each major table?

### **CI/CD Questions**
5. **Container Registry**: Should we use GitLab's registry (`registry.gitlab.com/brrm-group/project88-racedisplay-project`)?
6. **Branch Protection**: Should we enforce code review requirements on `dev` and `main` branches?

---

## 📊 **Success Metrics**

### **Infrastructure Metrics**
- [ ] Both environments deployed and accessible
- [ ] All 4 applications running on both VPSs
- [ ] Database connectivity verified
- [ ] SSL certificates active
- [ ] Backup procedures operational

### **CI/CD Metrics**
- [ ] GitLab pipeline fully functional
- [ ] Branch-based deployment working
- [ ] Security scans integrated
- [ ] Manual prod approval workflow active
- [ ] Rollback procedures tested

### **Operational Metrics**
- [ ] Email alerts configured and tested
- [ ] Health monitoring active
- [ ] Nightly dev refresh working
- [ ] S3 backups successful
- [ ] Zero-downtime deployments verified

---

## 🎯 **Risk Mitigation**

### **High-Risk Areas**
1. **Database Migration**: Test dev refresh extensively before production implementation
2. **Domain Configuration**: Verify DNS propagation for all dev subdomains
3. **SSL Certificates**: Ensure Let's Encrypt rate limits not exceeded
4. **ChronoTrack Collector**: Validate port 61611 works on both environments

### **Rollback Plans**
- **Infrastructure**: Ansible playbook rollback capabilities
- **Applications**: Docker image tagging for quick reverts  
- **Database**: Point-in-time recovery from S3 backups
- **CI/CD**: Manual override capabilities in GitLab

---

## 📝 **Implementation Checklist**

### **Pre-Implementation**
- [ ] Dev VPS provisioned and accessible
- [ ] AWS S3 bucket credentials available
- [ ] GitLab CI/CD access confirmed
- [ ] DNS configuration ready for dev subdomains

### **Phase 1 Completion**
- [ ] Ansible inventory files populated
- [ ] All roles created and tested
- [ ] Vault files encrypted and committed
- [ ] Environment-specific variables configured

### **Phase 2 Completion**
- [ ] GitLab CI pipeline functional
- [ ] Security scans operational
- [ ] Branch-based deployments working
- [ ] Container registry integration complete

### **Phase 3 Completion**
- [ ] Monitoring alerts configured
- [ ] Health checks operational
- [ ] Backup procedures verified
- [ ] Production deployment approved

---

## 🔄 **Post-Implementation Maintenance**

### **Weekly Tasks**
- Review GitLab CI pipeline performance
- Verify backup integrity
- Check SSL certificate expiration
- Monitor resource utilization

### **Monthly Tasks**
- Update Ansible roles and playbooks
- Review security scan results
- Audit user access and permissions
- Test disaster recovery procedures

---

**Implementation Status**: Ready to proceed pending final infrastructure details  
**Timeline**: 10 working days from dev VPS provisioning  
**Risk Level**: Low (building on proven production system)  
**Team**: DevOps with developer support

---

### **Change Log**
| Date | Author | Notes |
|------|--------|-------|
| 2025-07-02 | DevOps Team | Initial implementation plan created |