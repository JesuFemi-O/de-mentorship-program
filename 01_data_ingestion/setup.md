# Chapter 01: Data Ingestion

## Local Stack

This chapter uses the following services:

| Service    | Purpose          | Port |
|------------|------------------|------|
| PostgreSQL | Primary database | 5432 |

### Starting the stack

```bash
cp ../.env.example ../.env   # configure credentials if needed
cd ../infrastructure
docker compose up -d
```

### Stopping the stack

```bash
cd ../infrastructure
docker compose down      # stop containers
docker compose down -v   # stop and remove volumes (full reset)
```

> Volume data is mounted to `infrastructure/volumes/` — delete that folder for a clean slate.

---

## Database Tools

There are various options out there that give you the functionality of exploring your databases, and any is welcome. Here are a few I will recommend:

- [PostgreSQL VS Code extension](https://marketplace.visualstudio.com/items?itemName=ms-ossdata.vscode-pgsql) for Postgres
- [DBeaver Community Edition](https://dbeaver.io/download/) for different databases
- [pgAdmin](https://www.pgadmin.org/)

---
