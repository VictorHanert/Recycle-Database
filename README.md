# Fullstack Project
## Tech Stack

### Frontend
- **React** with Vite
- **React Router** for navigation
- **Tailwind CSS and MUI** for styling
- **Context API** for state management

### Backend
- **Python** with FastAPI
- **SQLAlchemy** ORM
- **Pydantic** for data validation
- **JWT** authentication
- **CORS** middleware

### Databases
- **MySQL** (primary database)
- **MongoDB** (document store)
- **Neo4j** (graph database)

### Testing
- **Jest** for frontend testing
- **Pytest** for backend testing

### Development & Deployment
- **Docker** & Docker Compose
- **Poetry** for Python dependency management
- **ESLint** for code linting

## Getting Started

### Start the Application

```bash
# Start platform

# Stop all services
docker-compose down
```

### Seed the Database
```bash
cd backend
poetry install
poetry run python seed.py
```

## Access Points

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs (Swagger UI)
- **API Documentation**: http://localhost:8000/redoc (ReDoc)
