## deployment_style.md

```markdown
# Deployment Style – Rolling Update

## 🎯 Overview

Project88 uses a **rolling update deployment strategy** to ensure zero-downtime deployments while maintaining service availability for our 13+ timing partners and live race events.

## 🔄 Deployment Philosophy

### Core Principles
- **Zero Downtime**: Race timing never stops
- **Gradual Rollout**: Deploy to one container at a time
- **Health Verification**: Ensure each instance is healthy before proceeding
- **Quick Rollback**: Ability to revert within seconds
- **Weekend Blackout**: No deployments during race weekends

## 📅 Maintenance Windows

| Environment | Deployment Window | Restrictions | Approval Required |
|-------------|------------------|--------------|-------------------|
| **Production** | Mon-Thu 14:00-17:00 ET | No weekends, no race days | Team Lead + Product |
| **Development** | Anytime | None | Developer |


## Manual Rollback Script

# Quick rollback script
#!/bin/bash
# rollback.sh

PREVIOUS_TAG=$(docker images --format "{{.Tag}}" | grep -v latest | head -2 | tail -1)

ansible-playbook deploy.yml \
  -e "image_tag=$PREVIOUS_TAG" \
  -e "skip_health_check=false" \
  --tags rollback