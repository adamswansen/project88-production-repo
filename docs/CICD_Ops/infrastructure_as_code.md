# Infrastructure‑as‑Code (IaC) – Project 88

> **File:** `infrastructure_as_code.md`\
> **Version:** v0.1 – 2025‑07‑01\
> **Maintainer:** DevOps Team

---

## 1  Objective

Provide an auditable, repeatable, one‑command path to **provision**, **configure**, and **deploy** Project 88 on any compatible VPS or IaaS instance.

---

## 2  Toolchain Overview

| Layer                    | Tool                                    | Why Chosen                                                                   |
| ------------------------ | --------------------------------------- | ---------------------------------------------------------------------------- |
| Configuration & Deploy   | **Ansible 2.16+**                       | Push model (no daemon), YAML syntax, idempotent, built‑in Vault              |
| Secrets                  | **Ansible Vault** + GitLab CI variables | Encrypts `.env` & DB creds in repo; CI supplies vault pass automatically     |

> **MVP Scope:** Ansible only. Terraform modules will be added when we migrate prod off WHM.

---

## 3  Repository Layout

```
infra/
  inventory.yml            # host groups: dev, prod
  group_vars/
    all.yml                # shared, non‑secret
    dev.yml                # dev overrides
    prod.yml               # 🔐 vaulted secrets
  roles/
    common/                # OS hardening, firewalld, users
    docker/                # Engine + compose‑v2 plugin
    postgres/              # optional local Postgres install/config
    project88/
      templates/
        docker‑compose.yml.j2
      tasks/main.yml       # pull & up -d
    backup/                # pg_dump + wal‑g timer units
  playbooks/
    site.yml               # full stack
    deploy.yml             # project88 role only
```

### 3.1  Inventory Example

```yaml
all:
  vars:
    ansible_user: centos
    ansible_ssh_private_key_file: ~/.ssh/p88_key
  children:
    prod:
      hosts:
        p88-prod.example.com:
          compose_project: p88
    dev:
      hosts:
        p88-dev.example.com:
          compose_project: p88dev
```

---

## 4  Key Roles & Responsibilities

| Role          | Tags    | Highlights                                                                                   |
| ------------- | ------- | -------------------------------------------------------------------------------------------- |
| **common**    | common  | hostname, `/etc/login.defs`, fail2ban, firewalld (80/443/22), timezone ET                    |
| **docker**    | docker  | yum‑config‑manager → Docker CE repo, install engine+cli, enable, usermod –aG docker `centos` |
| **project88** | project | Template compose file & `.env`, pull image tag, `docker compose up -d`, waits on health      |
| **backup**    | backup  | install lz4 + wal‑g, drop `pg_dump_p88.sh`, systemd timer 03:00, Prometheus‑push gating      |

---

## 5  Running Playbooks Locally

```bash
# Full bootstrap (common + docker + project88) on dev
ansible-playbook playbooks/site.yml -l dev -e "image_tag=latest"

# Deploy only a new image tag on prod
ansible-playbook playbooks/deploy.yml -l prod -e "image_tag=v2025.07.01-abc123"
```

The vault password is read from `ANSIBLE_VAULT_PASSWORD` env var or `--vault-password-file ~/vault_pass`.

---

## 6  CI/CD Integration

- GitLab Runner image: `ansible/ansible-runner:2`.
- Job `before_script` writes SSH key & vault pass to tmp files.
- CI variable `TARGET_ENV` maps to inventory group (`dev` or `prod`).

```yaml
.deploy_template: &deploy
  stage: deploy
  image: ansible/ansible-runner:2
  script:
    - ansible-playbook playbooks/deploy.yml -l $TARGET_ENV -e "image_tag=$CI_COMMIT_SHA"
```

---

## 7  Drift Detection & Auditing

- Weekly cron job in GitLab Pipeline runs `ansible-playbook --check` against prod; any `changed` results create an MR tagging Ops to reconcile.
- `ansible-lint` executed per MR to enforce best practices.

---

## 8  Future Enhancements

1. **Terraform modules**: ALB + ACM TLS termination, Route53 records, S3 bucket.
2. **Molecule tests** for role regression.
3. **Aqua Security Trivy‑role** to scan host packages during playbook run.

---

### Change Log

| Date       | Author | Notes         |
| ---------- | ------ | ------------- |
| 2025‑07‑01 | DevOps | Initial draft |

