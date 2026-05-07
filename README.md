# Data Engineering Mentorship Program

Worked examples covering data engineering design patterns, using a shared local stack and [kroft](https://github.com/JesuFemi-O/kroft) as the data generator.

Based on concepts from *Fundamentals of Data Engineering* by Bartosz.

---

## Local Stack

| Service | Purpose | Port |
|---------|---------|------|
| PostgreSQL | Primary database | 5432 |
| MinIO | Object storage (S3-compatible) | 9000 / 9001 (console) |
| Redpanda | Kafka-compatible message broker | 9092 |
| Schema Registry | Avro/Protobuf schema management | 8081 |
| Redpanda Console | Broker UI | 8080 |
| Kafka Connect | Source/sink connectors | 8083 |

### Starting the stack

```bash
cp .env.example .env   # configure credentials if needed
cd infrastructure
docker compose up -d
```

### Stopping the stack

```bash
docker compose down         # stop containers
docker compose down -v      # stop and remove volumes (full reset)
```

---

## Python Setup

```bash
uv sync
```

---

## Structure

```
de-mentorship-program/
├── infrastructure/          # shared docker-compose stack
├── shared/                  # reusable helpers (DB connection, kroft column definitions)
├── 01_data_ingestion/       # chapter 1
├── 02_batch_processing/     # chapter 2 (coming soon)
└── ...
```

Each chapter folder contains its own `README.md` explaining the concept and scripts demonstrating it.

---

## Chapters

| # | Topic | Status |
|---|-------|--------|
| 01 | Data Ingestion | In progress |
