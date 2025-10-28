# Database Course Backend Project

A FastAPI-based backend showcasing database integration with MySQL, MongoDB, and Neo4j.

## Tech Stack

### Backend
- **Python** with FastAPI
- **SQLAlchemy** ORM for MySQL
- **Pydantic** for data validation
- **JWT** authentication
- **Repository Pattern** for database abstraction

### Databases
- **MySQL** (primary relational database)
- **MongoDB** (document store) - *planned*
- **Neo4j** (graph database) - *planned*

### Development & Deployment
- **Docker** & Docker Compose
- **Poetry** for dependency management

## Getting Started

### Start the Application

```bash
# Start all services (backend + databases)
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop all services
docker-compose down
```

### Seed the Database
```bash
cd backend
poetry install
poetry run python seed.py
```
## API Access Points

- **Backend API**: http://localhost:8000
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health
