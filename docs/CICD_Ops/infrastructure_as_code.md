# Infrastructure‑as‑Code (IaC) – Project 88

File: `infrastructure_as_code.md`\
Version: **v0.3 – 2025‑07‑02**\
Maintainer: DevOps Team

---

## 1 Goal

Automate configuration, application deployment, and ongoing drift detection for the two long‑lived **Hostinger VPSs** (prod & dev) using **Ansible only**. The servers themselves are provisioned once via the Hostinger UI; everything else is codified so that any state can be reproduced with a single playbook run.

---

## 2 Toolchain Stack

| Layer                | Tool                                  | License | State backend              | Why we use it                                           |
| -------------------- | ------------------------------------- | ------- | -------------------------- | ------------------------------------------------------- |
| Host config & deploy | **Ansible 2.16**                      | GPL‑v3  | stateless (YAML playbooks) | Push model; idempotent tasks; Ansible Vault for secrets |
| Secrets              | Ansible Vault + GitLab CI masked vars | GPL‑v3  | —                          | Encrypt `.env`, DB creds                                |
| CI Runner            | GitLab CI/CD                          | MIT     | —                          | Automates lint, check, deploy stages                    |

---

## 3 Repository Layout

```
infra/
  ansible/
    inventory/
      dev.ini
      prod.ini
    group_vars/
      all.yml
      dev.yml          # vaulted
      prod.yml         # vaulted
    roles/
      common/          # hardening, users, fail2ban, etc.
      docker/
      project88/
      backup/
    playbooks/
      site.yml         # OS baseline + docker
      deploy.yml       # pull latest containers, restart
.gitlab-ci.yml
```

**Inventory management:** IPs/hostnames are recorded manually when a VPS is (re)built. Production and dev inventories live side‑by‑side so that CI can target either environment.

---

## 4 CI/CD Flow (high‑level)

```
           ┌────────────┐  ansible-playbook           ┌──────────────┐
GitLab CI ─┤  Ansible   ├────────────────────────────▶│  VPS (SSH)   │
           └─────┬──────┘                              └──────────────┘
                 ▲
                 │ lint / check-mode
                 │
           ┌────────────┐
           │ansible-lint│
           └────────────┘
```

- ``** stage** — runs `ansible-lint` + `yamllint` on every Merge Request.
- ``** job** — auto‑runs on commits to `dev` branch; targets `infra/ansible/inventory/dev.ini`.
- ``** job** — manual & protected; targets `prod.ini`.
- ``** scheduled job** — weekly `ansible-playbook site.yml --check` for both hosts; emails diff if tasks would change anything.

---

## 5 Granular Plan of Action

| Day | Deliverable                      | Detail                                                                     |
| --- | -------------------------------- | -------------------------------------------------------------------------- |
| 1   | Create `infra/ansible/` skeleton | inventory, group\_vars, roles                                              |
| 2   | Write `roles/common`             | users, SSH hardening, UFW, fail2ban                                        |
| 3   | Write `roles/docker`             | install Docker Engine & Compose plugin                                     |
| 4   | Write `roles/project88`          | pull images, compose up                                                    |
| 5   | Write `roles/backup`             | nightly pg\_dump → S3 (or Hostinger Object Storage)                        |
| 6   | Configure GitLab CI lint stage   | docker image `cytopia/ansible-lint`                                        |
| 7   | Add `deploy_dev` job             | `ansible-playbook -i inventory/dev.ini site.yml && deploy.yml`             |
| 8   | Secure secrets with Vault        | commit vaulted `dev.yml` & `prod.yml`; add CI var `ANSIBLE_VAULT_PASSWORD` |
| 9   | Protect `deploy_prod` job        | require manual approval                                                    |
| 10  | Schedule weekly drift check      | GitLab → CI/CD → Schedules                                                 |

---

## 6 Secrets Management

- **Vault files** (`group_vars/*/vault.yml`) encrypted with a shared passphrase stored as the masked variable `ANSIBLE_VAULT_PASSWORD`.
- **GitLab CI variables** for anything that should never enter git (API keys, DB root passwords).
- Vault split per‑environment so dev and prod secrets stay isolated.

---

## 7 Drift Detection

- **Ansible check‑mode:**
  ```bash
  ansible-playbook -i inventory/prod.ini site.yml --check --diff
  ```
  Exit code ≠ 0 or diff output → pipeline fails and notifies DevOps.
- **Server hardening enforcement:** `roles/common` runs every deploy, so any manual change (e.g., unauthorized user account) is reverted automatically.

---

## 8 Testing

1. **ansible‑lint** & **yamllint** on every MR.
2. **Molecule** scenario per role using Docker container images (`almalinux:9`), executed nightly.
3. **Testinfra** assertions (ports open, services running) as part of Molecule verify stage.

---

## 9 Future Improvements

- Migrate inventories to **Ansible Inventory Plugin for NetBox** if project adds many hosts.
- Use **GitLab Deploy‑ment environments** for richer history and rollback buttons.
- Replace manual IP recording with a tiny bash script that queries Hostinger API and rewrites the inventory files.

---

### Change Log

| Date       | Author | Note                                                     |
| ---------- | ------ | -------------------------------------------------------- |
| 2025‑07‑01 | DevOps | Initial Terraform + Ansible version                      |
| 2025‑07‑02 | DevOps | **Removed Terraform**; switched to pure‑Ansible approach |

