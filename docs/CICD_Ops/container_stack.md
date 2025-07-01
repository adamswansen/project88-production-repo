# Container Stack – Project 88

> **File:** `container_stack.md`  
> **Version:** v0.1 – 2025‑07‑01  
> **Maintainer:** DevOps Team

---

## 1  Scope & Principles
This document describes every containerised component that makes up the Project 88 application runtime, how they interact, and how they are defined in `docker‑compose.yml`.  
Key design principles:
* **Stateless services first** – Only PostgreSQL holds durable data.
* **Explicit health‑checks** – Compose waits before promotion during rolling updates.
* **12‑Factor env** – Every configuration item is supplied via `.env` or Vault.
* **Minimal images** – Alpine or slim variants, pinned by **digest** for prod.

---

## 2  Service Catalogue

| Service | Image (prod) | Purpose | Ports | Health check | Notes |
|---------|--------------|---------|-------|--------------|-------|
| `web` | `registry.gitlab.com/p88/app:<tag>` | FastAPI/uvicorn REST & WebSockets | 8000 | `GET /health` | CPU‑bound; replicas = 2 on prod via `deploy.replicas` |
| `worker` | same as web | Celery task queue (NLP, pdf, mail) | – | `celery ping` (exec) | No external port; binds to Redis |
| `db` | `postgres:16-alpine` | Primary relational store | 5432 | `pg_isready` | Volume `db_data` mounts `/var/lib/postgresql/data` |
| `redis` | `redis:7-alpine` | Celery broker, short‑term cache | 6379 | `redis-cli ping` | No persistence; can lose cache |
| `search` | `opensearchproject/opensearch:2` | Full‑text & embeddings index | 9200/9600 | `_cluster/health` | Single node; memory‑lock disabled; uses volume `search_data` |
| `traefik` (optional) | `traefik:v3.0` | Reverse proxy / TLS | 80,443 | `:8080/ping` | Labels route `web` traffic; handles LetsEncrypt |
| `grafana‑agent` | `grafana/agent:v0.40` | Logs & metrics shipper | 12345 | `/-/ready` | Sidecar pattern; sends to Grafana Cloud |

> **Dev‑only additions:** Mailhog (`mailhog/mailhog`) on port 8025, pgAdmin for DB UI.

---

## 3  Compose File Structure
### 3.1  Directory Layout
```
compose/
  docker-compose.yml            # canonical spec (Jinja2 template)
  env/
    base.env                    # common vars, non‑secret
    dev/web.env                 # dev overrides
    prod/web.env.vault          # 🔐 vaulted secrets
volumes/                        # named in compose
```

### 3.2  Important Snippets
```yaml
version: "3.9"
services:
  web:
    image: ${IMAGE_REPO}:${IMAGE_TAG}
    deploy:
      replicas: ${WEB_REPLICAS:-1}
      resources:
        limits: {cpus: "0.5", memory: "512m"}
    env_file:
      - env/${ENVIRONMENT}/web.env
    depends_on:
      db: {condition: service_healthy}
      redis: {condition: service_started}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 10s
      timeout: 3s
      retries: 5
```
* **Resource limits** prevent a noisy web process from starving the DB.
* `$ENVIRONMENT` is injected by Ansible (either `dev` or `prod`).

### 3.3  Networks & Security
* Single default bridge network: all containers resolve by service name.
* Optionally set `traefik.docker.network=webnet` for Traefik overlay.
* Inter‑container traffic is not TLS‑encrypted (trusted network)
  – assumption: host firewall blocks external access.

---

## 4  Data Persistence & Backups
| Volume | Mounted By | Backup Method |
|--------|------------|---------------|
| `db_data` | `db` | Nightly `pg_dump`, WAL streaming (see BU_recovery.md) |
| `search_data` | `search` | Not backed up – index can be rebuilt from Postgres |
| `redis` | – | None (ephemeral) |

Filesystem snapshots are not required; logical backups suffice.

---

## 5  Logs & Metrics
* **Stdout/stderr** for every container is in JSON. Docker daemon rotates at 100 MB, 3 files.
* `grafana‑agent` tails Docker socket and ships:
  * **Logs** → Loki `labels={service="$NAME", env="$ENV"}`
  * **Metrics** from `/metrics` endpoints (web, db, OS)
* Trace export (`OTEL_EXPORTER_OTLP_ENDPOINT`) lives in web & worker env.

---

## 6  Local Development Patterns
1. `make dev-up` → starts compose stack with live‑reload mounts.
2. Web code mount via `volumes: ./src:/app/src:ro` in an override file.
3. PG data uses a **tmpfs** in dev (`db_tmp`) to avoid accumulating test junk.
4. `docker compose logs -f web worker` prints combined logs.

---

## 7  Deployment Lifecycle
| Phase | Command | Detail |
|-------|---------|--------|
| **Pull** | `docker compose pull` | Fetch new images (Ansible task) |
| **Roll** | `docker compose up -d --wait --pull never` | Compose waits on health; old container stops post‑success |
| **Cleanup** | `docker image prune --filter until=168h` | Weekly cron frees unused layers |

---

## 8  Hardening Checklist
* All images pinned by **digest** in `prod.env` to avoid surprise tags.
* `read_only: true` for web & worker containers except `/tmp` mount when possible.
* `user: 1000:1000` (non‑root) set on custom images.
* `cap_drop: [ALL]` except `db`/`search` where upstream images require defaults.

---

### Change Log
| Date | Author | Summary |
|------|--------|---------|
| 2025‑07‑01 | DevOps | Initial draft |

