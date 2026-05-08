# Data Engineering Mentorship Program

Worked examples covering data engineering design patterns, using a shared local stack and [kroft](https://github.com/JesuFemi-O/kroft) as the data generator.

Based on *[Data Engineering Design Patterns](https://learning.oreilly.com/library/view/data-engineering-design/9781098165826/)* by Bartosz Konieczny.

---

## Python Setup

This project uses [uv](https://docs.astral.sh/uv/) to manage the virtual environment. If you don't have it installed, follow the [installation guide](https://docs.astral.sh/uv/#installation).

1. Create a virtual environment:

```bash
uv venv
```

This creates a `.venv` directory in the project.

2. Activate the virtual environment:

```bash
source .venv/bin/activate  # macOS/Linux
# or
.venv\Scripts\activate     # Windows
```

3. Install dependencies:

```bash
uv sync
```

You're now ready to run the examples and work through the chapters.

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

---

### Stopping the stack

```bash
docker compose down      # stop containers
docker compose down -v   # stop and remove volumes (full reset)
```

> Volume data is mounted to `infrastructure/volumes/` — delete that folder for a clean slate.


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
