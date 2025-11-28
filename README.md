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
Swagger docs: `http://localhost:8000/docs` (interactive testing)  
ReDoc: `http://localhost:8000/redoc` (clean documentation)  
OpenAPI schema: `http://localhost:8000/openapi.json`

### Postman Setup

Import the API into Postman for easy testing:
See **[postman/POSTMAN_SETUP.md](postman/POSTMAN_SETUP.md)** for detailed setup guide.

---

## Database Users & Security

Each database has 4 user types:
- **app_user**: Application connection (minimum privileges)
- **db_admin**: Full database administration
- **readonly_user**: Read-only access for analytics
- **restricted_user**: Limited access to non-sensitive data

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
### Repo 1: Fullstack Production App

recycle-marketplace/  (deployed to Azure)
├── frontend/          # React app on Vercel
├── backend/
│   ├── services/      # Full business logic
│   ├── repositories/mysql/
│   └── routers/mysql/
└── MySQL Database     # "Source of Truth"
---
### Repo 2: Databases for Mongo & Neo4j
recycle/
├── backend/
│   ├── routers/
│   │   ├── mongodb/   Document DB endpoints
│   │   └── neo4j/     Graph DB endpoints
│   ├── repositories/
│   │   ├── mongodb/   Direct DB access
│   │   └── neo4j/     Direct DB access
│   ├── models/
│       ├── mongodb/   # Pydantic schemas
│       └── (no neo4j models)
├── scripts/
│   ├── migrate_to_mongodb.py   # Read from Repo 1's MySQL
│   └── migrate_to_neo4j.py     # Read from Repo 1's MySQL
└── docker-compose.yml  # MongoDB + Neo4j only

---
### Architecture

Local Docker Architecture Diagram

  ```
                                CLIENT / SWAGGER UI
                               (Browser / Postman / Test)
                                          │
                                          │ HTTP Requests
                                          ▼
+──────────────────────────────────────────────────────────────────────────────────+
|                         FASTAPI BACKEND (Local Docker)                          |
|                                                                                  |
|   +──────────────────────+                    +─────────────────────+            |
|   | Router: /api/mongodb |                    |  Router: /api/neo4j |            |
|   +───────────┬──────────+                    +──────────┬──────────+            |
|               │                                          │                       |
|   +-----------▼──────────+                    +──────────▼──────────+            |
|   |  MongoDB Repository  |                    |   Neo4j Repository  |            |
|   |    (Motor/Pydantic)  |                    | (Neo4j Driver/Cypher)|           |
|   +───────────┬──────────+                    +──────────┬──────────+            |
|               │                                          │                       |
+───────────────┼──────────────────────────────────────────┼──────────────────────+
                │                                          │
                │ JSON Docs                                │ Cypher Nodes
                │                                          │
    +-----------▼──────────+                    +──────────▼────────────+
    |  MongoDB (Container) |                    |  Neo4j (Container)    |
    |   "Document Store"   |                    |    "Graph Store"      |
    | (Collections, Embeds)|                    | (Nodes, Relations)    |
    +──────────────────────+                    +───────────────────────+
                │                                          │
                │                                          │
                └──────────────────┬───────────────────────┘
                                   │
                      MIGRATION SCRIPTS (Python)
                      Read from Repo 1's Azure MySQL
                      Transform & Write to Local Databases
``` 





---
Cloud Architecture Diagram
┌─────────────────────────────────────────────────────────────┐
│  REPO 1: PRODUCTION FULLSTACK (recycle-marketplace)         │
│  ┌──────────────┐        ┌──────────────┐                   │
│  │   Frontend   │───────►│  Backend API │                   │
│  │   (Vercel)   │        │  (Azure App) │                   │
│  └──────────────┘        └───────┬──────┘                   │
│                                   │                         │
│                          ┌────────▼──────────┐              │
│                          │  MySQL (Azure)    │              │
│                          │  "Source of Truth"│              │
│                          └────────┬──────────┘              │
└──────────────────────────────────┼──────────────────────────┘
                                    │
                      Migration Scripts READ from here
                                    │
┌───────────────────────────────────▼───────────────────────────┐
│  REPO 2: EXAM PROJECT (recycle-exam)                          │
│  ┌──────────────────────────────────────────────────────┐     │
│  │  Backend API (Local Docker)                          │     │
│  │  ┌────────────────┐  ┌──────────────────┐           │      │
│  │  │ MongoDB Router │  │  Neo4j Router    │           │      │
│  │  └───────┬────────┘  └────────┬─────────┘           │      │
│  │          │                    │                     │      │
│  │  ┌───────▼────────┐  ┌────────▼─────────┐           │      │
│  │  │ MongoDB Repo   │  │  Neo4j Repo      │           │      │
│  │  └───────┬────────┘  └────────┬─────────┘           │      │
│  └──────────┼────────────────────┼─────────────────────┘      │
│             │                    │                            │
│  ┌──────────▼──────────┐  ┌──────▼──────────────┐             │
│  │ MongoDB Atlas       │  │ Neo4j AuraDB        │             │
│  │ (Cloud Cluster)     │  │ (Cloud Graph)       │             │
│  └─────────────────────┘  └─────────────────────┘             │
└───────────────────────────────────────────────────────────────┘
