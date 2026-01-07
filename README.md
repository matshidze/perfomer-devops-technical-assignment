# DevOps Technical Assignment

## What this project demonstrates
- Flask web app with HTML UI (submit text + display history)
- PostgreSQL persistence
- Dockerfile + Docker Compose orchestration
- Prometheus monitoring via /metrics
- DevOps readiness: health checks, logging, retries, CI quality gates
- Terraform IaC demo

## Architecture (high level)
User → Flask (web) → PostgreSQL  
Prometheus → scrapes Flask | metrics  
GitHub Actions → CI (lint + security + docker build)

## Quick start (Docker Compose)

### 1) Create `.env`
In project root:
```env
POSTGRES_USER=performeruser
POSTGRES_PASSWORD=performerpass
POSTGRES_DB=appdb
