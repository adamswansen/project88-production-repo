# Source‑Control & Release Management – Project 88

> **File:** `source_control.md`\
> **Version:** v0.1 – 2025‑07‑01\
> **Maintainer:** DevOps Team

---

## 1  Branching Strategy (Trunk‑based)

### 1.1  Branches

| Name               | Lifespan     | CI Target          | Deployment             |
| ------------------ | ------------ | ------------------ | ---------------------- |
| `main`             | permanent    | full pipeline      | **Prod** (manual gate) |
| `dev`              | permanent    | full pipeline      | **Dev VPS** (auto)     |
| `feature/<ticket>` | ≤ 5 days     | lint + unit + scan | none                   |
| `hotfix/<issue>`   | until merged | lint + scans       | optional direct prod   |

### 1.2  Git Rules

1. **Squash‑merge** enforced (linear history).
2. **Conventional Commit** headers required in squash title, e.g. `feat(api): add search filters`.
3. Merge **into ** `dev` by default; `hotfix/*` may target `main`.
4. Delete source branch after merge (GitLab setting).
5. Protected branches (`main`, `dev`) require:
   - Green CI ✔︎.
   - ≥ 1 code‑owner approval.
   - No outstanding “High” vulnerabilities.

### 1.3  Tags & Releases

- Tags created *only* by `deploy_prod` job.
- Format: `vYYYY.MM.DD-<short_sha>` (e.g., `v2025.07.01-a1b2c3`).
- Tag message auto‑generates release notes with `git log <prev_tag>..<new_tag> --oneline --no-merges`.
- GitLab Release created via API; Docker image `:${tag}` pushed as immutable.

---

## 2  Pull/Merge Request Workflow

1. **Create branch** from `dev` (or `main` for hotfix).
2. Commit early/often; push to remote.
3. Open Merge Request (MR):
   - Template autofills checklist (tests, docs, security scan results).
   - Assign reviewer per CODEOWNERS.
4. CI pipeline auto‑runs.
5. Address code review + CI failures.
6. Reviewer approves; author presses **Squash & Merge**.
7. Pipeline auto‑deploys to dev (if target `dev`).

### 2.1  MR Template Snippet

```md
### Summary
Fixes #ISSUE_ID – …

### Checklist
- [ ] Unit tests added/updated
- [ ] Docs updated (`/docs/`)
- [ ] Pipeline green
- [ ] No new Critical/High vulnerabilities
```

---

## 3  Hot‑fix Procedure

1. Branch from `main`: `hotfix/cron-null-ref`.
2. Push commit; open MR targeting `main` (skip‑review if sev‑1, but still require CI green).
3. Maintainer merges; manual **Deploy to Prod** button.
4. Cherry‑pick commit to `dev` or merge `main → dev` to realign trunks.
5. Post‑mortem attached to incident ticket within 48 h.

---

## 4  Code Ownership & Permissions

- **CODEOWNERS** file defines path ownership (e.g., `infra/* @devops`).
- Maintainers: lead dev + one SRE; Developers: rest of team.
- Branch protection prevents force‑push / tag deletion.
- `release/*` branches forbidden (we use tags, not long‑lived release branches).

---

## 5  Commit Message Linting

Pre‑commit hook (`.husky/commit-msg`) installs `@commitlint/config-conventional`; pipeline runs `commitlint --from $CI_COMMIT_SHA~1`.

---

## 6  Changelog Management

- Generated from tags by `git-chglog` and published under `/docs/changelog/` via GitLab Pages.

---

### Change Log

| Date       | Author | Notes         |
| ---------- | ------ | ------------- |
| 2025‑07‑01 | DevOps | Initial draft |

