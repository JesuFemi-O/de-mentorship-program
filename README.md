# Data Engineering Mentorship Program

Worked examples covering data engineering design patterns, using a shared local stack and [kroft](https://github.com/JesuFemi-O/kroft) as the data generator.

Based on *Data Engineering Design Patterns* by Bartosz Konieczny.

---

## Local Stack

Services are added to the stack progressively as chapters require them. The current stack:

| Service | Purpose | Port |
|---------|---------|------|
| PostgreSQL | Primary database | 5432 |

### Starting the stack

```bash
cp .env.example .env   # configure credentials if needed
cd infrastructure
docker compose up -d
```

### Stopping the stack

```bash
docker compose down      # stop containers
docker compose down -v   # stop and remove volumes (full reset)
```

> Volume data is mounted to `infrastructure/volumes/` — delete that folder for a clean slate.

---

## Python Setup

```bash
uv sync
```

---

## Structure

```
de-mentorship-program/
├── infrastructure/          # docker-compose stack (grows per chapter)
├── shared/                  # reusable helpers: DB connection, kroft column definitions
├── examples/                # standalone runnable scripts
├── 01_data_ingestion/       # chapter 1
└── ...                      # chapters added as we progress
```

Each chapter folder contains its own `README.md` explaining the concept and scripts demonstrating it.

---

## Chapters

| # | Topic | Status |
|---|-------|--------|
| 01 | Data Ingestion | In progress |
