# Data Engineering Mentorship Program

Worked examples covering data engineering design patterns, using a shared local stack and [kroft](https://github.com/JesuFemi-O/kroft) as the data generator.

Based on *Data Engineering Design Patterns* by Bartosz Konieczny.

---

## Prerequisites

- Docker + Docker Compose
- Python 3.10+
- [`uv`](https://docs.astral.sh/uv/) for Python dependency management
- `jq` and `awscli` (for `make deploy` bucket/connector targets)

---

## Quick start

```bash
# 1. Clone and install Python deps
uv sync

# 2. Configure environment
cp .env.example .env   # edit if needed — defaults work out of the box

# 3. Start the full stack
make up                # builds images, starts all services, runs health checks

# 4. Deploy connectors and S3 buckets
make deploy
```

The Redpanda Console UI is available at http://localhost:8080 once the stack is up.

---

## Local stack

All services are managed from the repo root via `make`. Never `cd infrastructure` and run compose directly — the Makefile handles the `-f` flag.

| Service | Purpose | Port |
|---|---|---|
| PostgreSQL 16 | CDC source database (WAL logical replication) | 5432 |
| Kafka (KRaft) | Message broker | 9092 |
| Schema Registry | Avro schema management | 8081 |
| Kafka Connect | Debezium CDC source + S3 sink | 8083 |
| Redpanda Console | Kafka/Connect web UI | 8080 |
| SeaweedFS S3 | S3-compatible object storage | 8333 |
| SeaweedFS Filer | SeaweedFS filer UI | 8888 |
| SFTP | File upload endpoint | 2222 |

### Common make targets

```bash
make up                    # start full stack (build + health check)
make down                  # stop containers
make clean                 # stop + remove named volumes
make clean-data            # stop + delete all bind-mounted data (infrastructure/data/)

make deploy                # create S3 buckets + deploy all connectors (idempotent)
make verify                # health-check every service
make smoke                 # insert a CDC test row into postgres

make logs SVC=kafka        # tail logs for a specific service
make topics-list           # list all Kafka topics
make connectors-status     # show connector task states
make ps                    # show running containers
```

Run `make help` to see all available targets.

### Data persistence

Bind-mounted state lands in `infrastructure/data/` (gitignored). Delete it for a full clean slate:

```bash
make clean-data
```

---

## Python setup

```bash
uv sync          # install all dependencies
uv run ruff check .   # lint
uv run pytest    # run tests
```

Dependencies are declared in `pyproject.toml`. The `shared/` package is importable from any chapter script via `sys.path.insert(0, "../..")`.

---

## Environment variables

Copy `.env.example` to `.env` at the repo root. The Makefile and docker-compose pick it up automatically.

| Variable | Default | Purpose |
|---|---|---|
| `COMPOSE_PROJECT_NAME` | `cdcraft` | Docker project namespace |
| `POSTGRES_USER` | `postgres` | Postgres credentials |
| `POSTGRES_PASSWORD` | `postgres` | Postgres credentials |
| `POSTGRES_DB` | `cdcdemo` | Default database name |
| `S3_ACCESS_KEY` | `seaweed` | SeaweedFS S3 access key |
| `S3_SECRET_KEY` | `seaweed123` | SeaweedFS S3 secret |
| `S3_ENDPOINT` | `http://localhost:8333` | SeaweedFS S3 endpoint |
| `CONNECT_URL` | `http://localhost:8083` | Kafka Connect REST API |
| `KAFKA_BROKER` | `localhost:9092` | Kafka bootstrap server |

---

## Structure

```
de-mentorship-program/
├── .env.example                  # environment template
├── Makefile                      # all infra commands
├── pyproject.toml
├── infrastructure/
│   ├── docker-compose.yml
│   ├── kafka-connect/Dockerfile  # Debezium + Avro + S3 sink
│   ├── postgres/init.sql         # inventory schema + seed data
│   ├── connectors/               # Kafka Connect configs
│   ├── buckets/                  # S3 bucket definitions
│   └── seaweed/                  # SeaweedFS S3 identity config
├── shared/
│   ├── db.py                     # PostgreSQL connection factory
│   └── columns.py                # kroft column definitions (ORDERS_COLUMNS)
├── examples/
│   └── interactive.py            # kroft simulation CLI
└── 01_data_ingestion/
    └── nafdac/
        └── ingest_nafdac.py      # scrapes ~11 700 NAFDAC Greenbook products
```

Each chapter folder has its own `README.md` explaining the concept and how to run its scripts.

---

## Chapters

| # | Topic | Status |
|---|---|---|
| 01 | Data Ingestion | In progress |
