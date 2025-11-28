# Marketplace Backend – Database Course Final Project

**Exam Project: Document & Graph Database Implementation**

This repository demonstrates implementing the same marketplace functionality using **MongoDB (document)** and **Neo4j (graph)** databases, migrating data from a production MySQL system. The project showcases database-specific design patterns: denormalization for documents and relationship-driven modeling for graphs.

**Companion Repository**: [recycle-marketplace](https://github.com/VictorHanert/Recycle-Fullstack-Project) (Production MySQL fullstack with Azure deployment)

---

## Project Goals

- **Data Migration**: Transform relational MySQL data into document and graph structures
- **Equivalent Functionality**: Implement full CRUD operations across both database paradigms
- **Architecture Comparison**: Demonstrate how database design influences application structure
- **Exam Requirement**: "Store the same data and query the same information – design and structure will be different"

---

## Tech Stack

- **Python 3.13** / FastAPI / Pydantic
- **MongoDB** – embedded documents, text search, aggregations (Motor async driver)
- **Neo4j** – graph relationships, recommendations (async driver with Cypher)
- **Docker Compose** for local orchestration

---

## Quick Start

```bash
# Start MongoDB and Neo4j databases
docker compose up -d

# View backend logs
docker compose logs -f python-backend

# Stop all services
docker compose down
```

**Access Points:**
- Backend API: `http://localhost:8001`
- Swagger docs: `http://localhost:8001/docs`
- ReDoc: `http://localhost:8001/redoc`

---

## Data Migration from MySQL

This repository reads from the production MySQL database (separate repo) and transforms data for MongoDB and Neo4j:

```bash
# Migrate to MongoDB (denormalized documents with embedded data)
docker compose exec python-backend poetry run python -m scripts.migrate_to_mongodb

# Migrate to Neo4j (graph nodes and relationships)
docker compose exec python-backend poetry run python -m scripts.migrate_to_neo4j
```

Migrations are **idempotent** and safe to rerun.

---

## API Endpoints

Both databases implement the same core functionality with database-specific optimizations:

### MongoDB Endpoints (`/mongodb/products`)
- `POST /` - Create product (embedded seller/category)
- `GET /` - List products with filters
- `GET /{id}` - Get product by ID
- `PUT /{id}` - Update product
- `DELETE /{id}` - Delete product
- `PATCH /{id}/mark-sold` - Mark as sold
- `PATCH /{id}/toggle-status` - Toggle active/paused
- `POST /{id}/view` - Track view (embedded in document)
- `GET /filter` - Advanced search (text, price, tags)
- `GET /top-categories` - Aggregation pipeline
- `GET /popular` - Sort by view_count

### Neo4j Endpoints (`/neo4j/products`)
- `POST /` - Create product + CREATED relationship
- `GET /` - List products
- `GET /{id}` - Get product by ID
- `PUT /{id}` - Update product node
- `DELETE /{id}` - Delete product + relationships
- `PATCH /{id}/mark-sold` - Update status property
- `PATCH /{id}/toggle-status` - Toggle status
- `POST /{id}/view` - Create VIEWED relationship
- `POST /{id}/favorite` - Create FAVORITED relationship
- `GET /{id}/recommendations` - Graph traversal (collaborative filtering)
- `GET /popular` - Sort by view_count property

---

## Database Design Patterns

### MongoDB (Document Store)
- **Denormalization**: Seller, category, location embedded in product documents
- **No joins**: All related data retrieved in single query
- **Embedded arrays**: price_history, recent_views stored in product document
- **Text search**: Full-text index on title/description
- **Aggregation pipelines**: Group, sort, limit for analytics
- **Validation**: Pydantic models enforce schema at application layer

**Example Document:**
```json
{
  "_id": ObjectId("..."),
  "title": "Mountain Bike",
  "seller": {
    "id": "123",
    "username": "john_doe",
    "full_name": "John Doe"
  },
  "category": {
    "id": "5",
    "name": "Mountain Bikes"
  },
  "price_history": [
    {"amount": 5000, "currency": "DKK", "changed_at": "2024-01-01T..."}
  ],
  "stats": {
    "view_count": 42,
    "favorite_count": 3
  }
}
```

### Neo4j (Graph Store)
- **Relationships over embedding**: CREATED, FAVORITED, VIEWED, IN_CATEGORY
- **No models needed**: Cypher queries return dynamic node properties
- **Graph traversal**: Recommendations via shared user interactions
- **Authorization via relationships**: Check CREATED edge for ownership
- **Counters as properties**: view_count, favorite_count on Product node

**Example Graph:**
```cypher
(:User {username: "john_doe"})-[:CREATED]->
(:Product {id: "uuid", title: "Mountain Bike", status: "active"})-[:IN_CATEGORY]->
(:Category {name: "Mountain Bikes"})

(:User {username: "jane"})-[:FAVORITED]->(:Product)
(:User {username: "bob"})-[:VIEWED]->(:Product)
```

---

## Architecture Differences

| Aspect | MongoDB | Neo4j |
|--------|---------|-------|
| **Schema** | Flexible documents (Pydantic validation) | Schema-less nodes/relationships |
| **Related Data** | Embedded (denormalized) | Relationships (normalized) |
| **Authorization** | Check embedded seller.id | Traverse CREATED relationship |
| **Queries** | Aggregation pipelines | Cypher pattern matching |
| **Service Layer** | ❌ None (inline router logic) | ❌ None (Cypher handles complexity) |
| **Models** | ✅ Pydantic for validation | ❌ Direct dict from Cypher |
| **Best For** | Read-heavy, document-centric | Relationship-heavy, recommendations |

---

## Project Structure

```
app/
  routers/
    mongodb/           # Document DB endpoints (no service layer)
    neo4j/             # Graph DB endpoints (no service layer)
  repositories/
    mongodb/           # Motor/PyMongo data access
    neo4j/             # Neo4j async driver with Cypher
  models/
    mongodb/           # Pydantic models for validation
    mysql/             # SQLAlchemy models (reference only)
scripts/
  migrate_to_mongodb.py  # Transform MySQL → MongoDB
  migrate_to_neo4j.py    # Transform MySQL → Neo4j
  mongodb/
    create_users.js        # MongoDB users & roles
  neo4j/
    create_users.cypher    # Neo4j users (Enterprise)
  dumps/
    dump_mongodb.sh
    dump_neo4j.sh
docker-compose.yml      # MongoDB + Neo4j + Backend
```

**Key Differences from MySQL Repository:**
- ❌ No service layer (business logic inline in routers)
- ❌ No file upload service (images stored as URLs only)
- ✅ Direct repository → router pattern (simpler for document/graph operations)
- ✅ Authorization checks inline (ownership via embedded data or relationships)

---
## Architecture

### Local Docker Architecture

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
|   | Router: /mongodb     |                    |  Router: /neo4j     |            |
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
                      Read from Production MySQL Database
                      Transform & Write to Local Databases
```

### Two-Repository Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  REPO 1: PRODUCTION FULLSTACK (recycle-marketplace)         │
│  ┌──────────────┐        ┌──────────────┐                  │
│  │   Frontend   │───────►│  Backend API │                  │
│  │   (Vercel)   │        │  (Azure App) │                  │
│  └──────────────┘        └───────┬──────┘                  │
│                                   │                          │
│                          ┌────────▼──────────┐              │
│                          │  MySQL (Azure)    │              │
│                          │  "Source of Truth"│              │
│                          └────────┬──────────┘              │
└──────────────────────────────────┼───────────────────────────┘
                                    │
                      Migration Scripts READ from here
                                    │
┌───────────────────────────────────▼───────────────────────────┐
│  REPO 2: EXAM PROJECT (this repository)                       │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  Backend API (Local Docker)                          │    │
│  │  ┌────────────────┐  ┌──────────────────┐           │    │
│  │  │ MongoDB Router │  │  Neo4j Router    │           │    │
│  │  └───────┬────────┘  └────────┬─────────┘           │    │
│  │          │                    │                      │    │
│  │  ┌───────▼────────┐  ┌────────▼─────────┐           │    │
│  │  │ MongoDB Repo   │  │  Neo4j Repo      │           │    │
│  │  └───────┬────────┘  └────────┬─────────┘           │    │
│  └──────────┼────────────────────┼──────────────────────┘    │
│             │                    │                            │
│  ┌──────────▼──────────┐  ┌──────▼──────────────┐           │
│  │ MongoDB (Local/Cloud)│  │ Neo4j (Local/Cloud) │           │
│  │ (Docker or Atlas)   │  │ (Docker or AuraDB)  │           │
│  └─────────────────────┘  └─────────────────────┘           │
└────────────────────────────────────────────────────────────────┘
```

**Design Rationale:**
- **Repo 1** = Production-grade MySQL fullstack (service layer, file uploads, Azure deployment)
- **Repo 2** = Exam-focused database comparison (no service layer, simpler architecture)
- **MySQL** remains authoritative source; MongoDB/Neo4j demonstrate alternative designs
- Keeps production code clean while showcasing database-specific patterns

---

## Database Users & Security

Both databases support 4 user types (see `scripts/mongodb/create_users.js` and `scripts/neo4j/create_users.cypher`):
- **app_user**: Application connection (minimum privileges)
- **db_admin**: Full database administration
- **readonly_user**: Read-only access for analytics
- **restricted_user**: Limited access to non-sensitive collections/nodes

---

## Tests

```bash
docker compose exec python-backend poetry run pytest
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
