# Alembic Migrations

This directory contains database migration scripts managed by Alembic.

## Commands

### Create a new migration (auto-generate from models)
```bash
alembic revision --autogenerate -m "description of changes"
```

### Apply migrations
```bash
# Upgrade to latest
alembic upgrade head

# Upgrade one version
alembic upgrade +1

# Downgrade one version
alembic downgrade -1
```

### View migration history
```bash
alembic history
alembic current
```

