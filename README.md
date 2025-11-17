# Marketplace Backend – Database Course Final Project

FastAPI backend implementing a marketplace system across three database types: MySQL (relational), MongoDB (document), and Neo4j (graph).

---

## Tech Stack

- **Python** / FastAPI / SQLAlchemy / Pydantic
- **MySQL** – stored procedures, triggers, views, events, audit logging
- **MongoDB** – embedded documents, text search, aggregations
- **Neo4j** – graph relationships, recommendations
- **Docker Compose** for orchestration

---

## Quick Start

```bash
# Start all services (MySQL, MongoDB, Neo4j, backend)
docker compose up -d

# View logs
docker compose logs -f python-backend

# Stop
docker compose down
```

Backend runs on: `http://localhost:8000`  
Swagger docs: `http://localhost:8000/docs`

The MySQL database is automatically seeded with test data on first startup.

---

## Migrate Data to MongoDB & Neo4j

After MySQL is populated, migrate data to the other databases:

```bash
docker compose exec python-backend poetry run python -m scripts.migrate_to_mongodb
docker compose exec python-backend poetry run python -m scripts.migrate_to_neo4j
```

Migrations are **idempotent** – safe to run multiple times.

---

## Database Dumps (for submission)

```bash
# MySQL dump (includes schema, procedures, triggers, views, events, data)
bash scripts/dumps/dump_mysql.sh

# MongoDB dump
bash scripts/dumps/dump_mongodb.sh

# Neo4j dump
bash scripts/dumps/dump_neo4j.sh
```

Dumps are saved to `scripts/dumps/` with timestamps.

---

## API Endpoints (Parallel Namespaces)

Same functionality across all three databases:

```
MySQL:
  /api/products, /api/auth/login, /api/auth/register

MongoDB:
  /api/mongodb/products
  /api/mongodb/products/filter          (advanced search)
  /api/mongodb/products/top-categories  (aggregation)

Neo4j:
  /api/neo4j/products
  /api/neo4j/products/{id}/recommendations  (graph traversal)
```

---

## MySQL Features

- **10+ entities**: users, products, categories, locations, favorites, messages, etc.
- **Stored procedures**: `ArchiveSoldProduct`, `GetProductRecommendations`, etc.
- **Triggers**: audit log on product insert/update/delete; auto-update view/like counters
- **Views**: `vw_public_products`, `vw_popular_products`
- **Events**: scheduled task to pause old inactive products
- **User privileges**: app user, admin, read-only, restricted read (see `scripts/mysql/create_users.sql`)

---

## MongoDB Features

- **Embedded documents**: seller, category, location inside product docs (denormalized)
- **Text index**: full-text search on title/description
- **Aggregation**: top categories by product count
- **Filtered search**: combine text, price range, status, seller, tags

---

## Neo4j Features

- **Nodes**: User, Product
- **Relationships**: `(:User)-[:CREATED]->(:Product)`, `[:FAVORITED]`, `[:VIEWED]`
- **Recommendations**: "users who favorited this also favorited..."

---

## Tests

```bash
docker compose exec python-backend poetry run pytest
```

---

## Project Structure

```
app/
  db/              # MySQL, MongoDB, Neo4j connections
  models/          # SQLAlchemy + Pydantic models
  repositories/    # Data access layer (MySQL, MongoDB, Neo4j)
  routers/         # API endpoints
  services/        # Business logic
scripts/
  mysql/           # init_database.sql, create_users.sql
  migrate_to_mongodb.py
  migrate_to_neo4j.py
  dumps/           # dump scripts
tests/             # Integration tests
docker-compose.yml
```

---

