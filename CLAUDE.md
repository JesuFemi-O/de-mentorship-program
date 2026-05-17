# CLAUDE.md — de-mentorship-program

This file is the source of truth for how Claude should understand and work in this repo. Keep it updated whenever the stack, structure, or conventions change.

---

## What this repo is

Worked examples teaching data engineering design patterns, based on *Data Engineering Design Patterns* by Bartosz Konieczny. Each chapter lives in its own numbered folder. The local stack grows as chapters require new services.

---

## Stack

All services are defined in `infrastructure/docker-compose.yml`. Managed from the repo root via `make`.

| Service | Image | Port | Purpose |
|---|---|---|---|
| postgres | postgres:16 | 5432 | CDC source database (WAL logical replication enabled) |
| kafka | confluentinc/cp-kafka:7.7.1 | 9092 | Message broker (KRaft mode, no ZooKeeper) |
| schema-registry | confluentinc/cp-schema-registry:7.7.1 | 8081 | Avro schema management |
| kafka-connect | custom (Debezium 3.5 base) | 8083 | CDC + S3 sink connectors |
| redpanda-console | redpandadata/console:latest | 8080 | Kafka/Connect web UI |
| seaweed-master | chrislusf/seaweedfs | — | SeaweedFS master node |
| seaweed-volume | chrislusf/seaweedfs | — | SeaweedFS volume node |
| seaweed-filer | chrislusf/seaweedfs | 8888 | SeaweedFS filer node |
| seaweed-s3 | chrislusf/seaweedfs | 8333 | S3-compatible API (replaces MinIO) |
| sftp | atmoz/sftp | 2222 | SFTP upload endpoint |

Kafka-connect image is built from `infrastructure/kafka-connect/Dockerfile` (adds Avro converter + S3 sink plugin on top of Debezium).

Bind-mounted data lives in `infrastructure/data/` — this directory is gitignored and safe to delete for a clean slate.

---

## Environment

`.env` lives at the repo root. Copy from `.env.example` to get started. The Makefile auto-loads it via `-include .env`.

Key variables:

```
COMPOSE_PROJECT_NAME=cdcraft
POSTGRES_USER / POSTGRES_PASSWORD / POSTGRES_DB
S3_ACCESS_KEY / S3_SECRET_KEY / S3_ENDPOINT
CONNECT_URL / KAFKA_BROKER
```

The `docker-compose.yml` uses `${VAR:-default}` syntax so the stack works without a `.env` file for local defaults.

---

## Makefile

The `Makefile` at the repo root is the single entry point for all infrastructure operations. It always passes `-f infrastructure/docker-compose.yml` to docker compose, so **never `cd` into `infrastructure/` to run compose directly**.

Key targets:

| Target | What it does |
|---|---|
| `make up` | Build + start full stack, then runs `verify` |
| `make down` | Stop and remove containers |
| `make clean` | Stop and remove containers + named volumes |
| `make clean-data` | Stop containers + `sudo rm -rf infrastructure/data/` |
| `make deploy` | Create S3 buckets + deploy all connectors (idempotent) |
| `make verify` | Health-check every service |
| `make smoke` | Insert a test row to trigger CDC end-to-end |
| `make logs SVC=kafka` | Tail logs for a specific service |
| `make topics-list` | List all Kafka topics |
| `make connectors-status` | Show connector task states |

Bucket definitions: `infrastructure/buckets/buckets.json`
Connector configs: `infrastructure/connectors/*.json`
SeaweedFS S3 identity: `infrastructure/seaweed/s3-config.json`
Postgres init SQL: `infrastructure/postgres/init.sql`

---

## Python

- Runtime: Python 3.10+
- Package manager: `uv` — run `uv sync` to install
- Entry point for DB connections: `shared/db.py` (`get_connection()`)
- Shared column definitions for kroft: `shared/columns.py` (`ORDERS_COLUMNS`)
- Linter: `ruff` (line length 88)
- Tests: `pytest` (run from repo root)

Scripts use `sys.path.insert(0, "../..")` to import from `shared/` — keep this pattern consistent across chapters.

---

## Repo structure

```
de-mentorship-program/
├── .env.example                  # template — copy to .env at repo root
├── .gitignore
├── CLAUDE.md                     # this file
├── Makefile                      # all infra commands, points into infrastructure/
├── pyproject.toml
├── README.md
├── infrastructure/
│   ├── docker-compose.yml        # full service stack
│   ├── kafka-connect/
│   │   └── Dockerfile            # Debezium + Avro converter + S3 sink
│   ├── postgres/
│   │   └── init.sql              # inventory schema + seed + WAL setup
│   ├── connectors/
│   │   ├── postgres-inventory-source.json
│   │   └── s3-cdc-sink.json
│   ├── buckets/
│   │   └── buckets.json
│   ├── seaweed/
│   │   └── s3-config.json
│   └── data/                     # gitignored — bind-mounted runtime state
├── shared/
│   ├── db.py
│   └── columns.py
├── examples/
│   └── interactive.py
└── 01_data_ingestion/
    └── nafdac/
        └── ingest_nafdac.py
```

---

## Conventions

- New chapters go in a new numbered folder: `02_<topic>/`, `03_<topic>/`, etc.
- Each chapter folder should have its own `README.md` explaining the concept and how to run its scripts.
- Chapter scripts import shared utilities via `sys.path.insert(0, "../..")` + `from shared.x import y`.
- New services required by a chapter are added to `infrastructure/docker-compose.yml` — update the stack table in both this file and `README.md` when you do.
- New environment variables go in `.env.example` first, then document them in the `.env` section of this file.
- Connector configs live in `infrastructure/connectors/` and are deployed via `make connectors`.
- `infrastructure/data/` is never committed — it is the only place bind-mounted state should land.

---

## Keeping this file accurate

**Update CLAUDE.md whenever you:**
- Add or remove a service from `docker-compose.yml` (update the stack table)
- Add a new chapter folder (update the structure tree and Chapters table in README.md)
- Add new environment variables (update the `.env` section and `.env.example`)
- Add new Makefile targets (update the targets table)
- Change the Python version, package manager, or linter config
- Move or rename any top-level directory

CLAUDE.md and README.md should always agree on the stack, ports, and structure. If they diverge, CLAUDE.md is authoritative.
