# GitLab CI/CD Pipeline – Project 88

> **File:** `gitlab_pipeline.md`\
> **Version:** v0.1 – 2025‑07‑01\
> **Maintainer:** DevOps Team

---

## 1  Pipeline Overview

```
lint → build → test → security → deploy_dev → integration → deploy_prod (manual)
```

Runs on GitLab SaaS with **Docker executor**.

---

## 2  Stage & Job Detail

| Stage            | Job                   | Image                      | Key Steps                                                    | Artifacts                        |
| ---------------- | --------------------- | -------------------------- | ------------------------------------------------------------ | -------------------------------- |
| **lint**         | `ansible-lint`        | `cytopia/ansible-lint`     | Scan `infra/` playbooks                                      | ‑                                |
|                  | `ruff`                | `python:3.11-slim`         | `ruff check .`                                               | ‑                                |
| **build**        | `docker-build`        | `docker:25` (dind)         | Build image, tag `:sha :branch :latest`, push to registry    | SBOM JSON                        |
| **test**         | `pytest`              | same as build              | `pytest -q && coverage xml`                                  | `coverage.xml`                   |
| **security**     | templated jobs        | GitLab Premium templates   | SAST, Dependency, Container, Secret Detection, DAST, License | scan reports auto‑uploaded       |
| **deploy\_dev**  | `ansible-deploy-dev`  | `ansible/ansible-runner:2` | Playbook `deploy.yml` to dev, image tag = `$CI_COMMIT_SHA`   | ‑                                |
| **integration**  | `smoke-e2e`           | `python:3.11-slim`         | Run REST smoke tests vs `https://p88-dev.example.com`        | JUnit XML                        |
| **deploy\_prod** | `ansible-deploy-prod` | same as deploy\_dev        | Manual, protected, deploys to prod                           | creates Git tag & GitLab Release |

### 2.1  Job Dependencies

`pytest` depends on `docker-build` image artifact via Docker registry pull; `container` scanning re‑uses built layers (template handles).

---

## 3  Core `.gitlab-ci.yml` Snippet

```yaml
variables:
  DOCKER_TLS_CERTDIR: ""
  IMAGE_REPO: $CI_REGISTRY_IMAGE
  IMAGE_TAG: $CI_COMMIT_SHA

stages: [lint, build, test, security, deploy]

include:
  - template: SAST.gitlab-ci.yml
  - template: Dependency-Scanning.gitlab-ci.yml
  - template: Container-Scanning.gitlab-ci.yml
  - template: Secret-Detection.gitlab-ci.yml
  - template: DAST.gitlab-ci.yml
  - template: License-Scanning.gitlab-ci.yml

lint:ansible:
  stage: lint
  image: cytopia/ansible-lint
  script: ["ansible-lint infer/"]

build:image:
  stage: build
  image: docker:25
  services: [docker:25-dind]
  script:
    - docker build -t $IMAGE_REPO:$IMAGE_TAG .
    - docker push $IMAGE_REPO:$IMAGE_TAG

pytest:
  stage: test
  image: python:3.11-slim
  script:
    - pip install -r requirements.txt
    - pytest -q --junitxml=report.xml
  artifacts:
    reports:
      junit: report.xml

.deploy_template: &ansible_deploy
  stage: deploy
  image: ansible/ansible-runner:2
  before_script:
    - echo "$ANSIBLE_SSH_KEY" > ~/.ssh/id_rsa && chmod 600 ~/.ssh/id_rsa
    - mkdir -p ~/.ssh && ssh-keyscan p88-dev.example.com p88-prod.example.com >> ~/.ssh/known_hosts
  script:
    - ansible-playbook infra/playbooks/deploy.yml -l $TARGET_ENV -e "image_tag=$IMAGE_TAG"

deploy_dev:
  <<: *ansible_deploy
  variables: { TARGET_ENV: "dev" }
  only: [dev]

deploy_prod:
  <<: *ansible_deploy
  variables: { TARGET_ENV: "prod" }
  only: [main]
  when: manual
  environment:
    name: production
    url: https://p88-prod.example.com
  after_script:
    - ./scripts/tag_release.sh $IMAGE_TAG
```

---

## 4  Secrets & CI Variables

| Variable                    | Scope     | Purpose                            |
| --------------------------- | --------- | ---------------------------------- |
| `ANSIBLE_SSH_KEY`           | protected | Private key for VPS access         |
| `ANSIBLE_VAULT_PASSWORD`    | protected | Decrypts vault files               |
| `CI_REGISTRY_USER/PASSWORD` | protected | Pull from registry during playbook |
| `DAST_WEBSITES`             | all       | `https://p88-dev.example.com`      |

---

## 5  Security Scan Policies

- **Block merge** when SAST/Dependency/Container report **High/Critical**.
- **Secret Detection** – pipeline fails on any leak (set `FAIL_OPEN:false`).
- **DAST** – informational; MR comment produced.
- **License Scan** – block if Blacklist (GPL‑3+). Allow Apache/MIT/BSD.

---

## 6  Manual Ops Buttons

GitLab **Run Pipeline** UI allows:

- ``** override** – deploy previously built image (rollback).
- `` – hot reload.

---

## 7  Pipeline Runtime Targets

| Stage       | Target time             |
| ----------- | ----------------------- |
| lint        | < 30 s                  |
| build       | < 2 min (layer cache)   |
| test        | < 1 min                 |
| security    | 3–4 min                 |
| deploy\_dev | < 90 s (pull + restart) |

---

### Change Log

| Date       | Author | Notes         |
| ---------- | ------ | ------------- |
| 2025‑07‑01 | DevOps | Initial draft |

