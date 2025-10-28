# Database Course Backend Project

A FastAPI-based backend showcasing database integration with MySQL, MongoDB, and Neo4j.

## Tech Stack

### Backend
- **Python** with FastAPI
- **SQLAlchemy** ORM for MySQL
- **Pydantic** for data validation
- **JWT** authentication
- **Repository Pattern** for database abstraction
- **Alembic** for database migrations

### Databases
- **MySQL** (primary relational database)
- **MongoDB** (document store) - *planned*
- **Neo4j** (graph database) - *planned*

### Development & Deployment
- **Docker** & Docker Compose
- **Poetry** for dependency management
- **pytest** for testing
- **GitHub Actions** for CI/CD

## Project Structure

```
/
├── app/                    # FastAPI application
│   ├── models/            # SQLAlchemy models
│   ├── routers/           # API endpoints
│   ├── services/          # Business logic
│   ├── repositories/      # Data access layer
│   ├── schemas/           # Pydantic schemas
│   └── db/                # Database connections
├── tests/                 # Test suite
├── alembic/               # Database migrations
├── scripts/               # Utility scripts (seed, etc.)
├── Dockerfile             # Production image
├── Dockerfile.dev         # Development image
└── docker-compose.yml     # Local development setup
```

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
poetry install
poetry run python scripts/seed.py
```

### Run Tests
```bash
# Install dependencies
poetry install

# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=app

# Run specific test file
poetry run pytest tests/test_api.py
```
## API Access Points

- **Backend API**: http://localhost:8000
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## Docker

### Development
Uses `Dockerfile.dev` with hot-reload enabled via docker-compose.

### Production
The main `Dockerfile` is a multi-stage build optimized for production:
- Stage 1: Builder - installs dependencies
- Stage 2: Runtime - lightweight image with only necessary files
- Non-root user for security
- Health checks included

Build production image:
```bash
docker build -t recycle-backend:latest .
```

## CI/CD

GitHub Actions workflow runs on every push and PR:
- Linting with pylint
- Tests with pytest
- Coverage reporting
- Docker image build validation

## Deployment to Azure

This backend is ready for Azure deployment via:
- **Azure App Service** (recommended for simplicity)
- **Azure Container Apps** (for microservices)
- **Azure Kubernetes Service (AKS)** (for complex orchestration)

### Environment Variables for Production
Set these in Azure App Service Configuration:
- `DATABASE_URL` - MySQL connection string
- `MONGODB_URL` - MongoDB connection string  
- `NEO4J_URL`, `NEO4J_USER`, `NEO4J_PASSWORD` - Neo4j credentials
- `SECRET_KEY` - JWT secret (use Azure Key Vault)
- `ENVIRONMENT=production`

## Development

### Local Setup Without Docker
```bash
# Install dependencies
poetry install

# Set up environment
cp .env.example .env
# Edit .env with your database credentials

# Run database migrations
poetry run alembic upgrade head

# Seed database
poetry run python scripts/seed.py

# Run the application
poetry run uvicorn app.main:app --reload
```
