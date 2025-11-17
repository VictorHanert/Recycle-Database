FROM python:3.13-slim

RUN ln -sf /usr/local/bin/python3 /usr/local/bin/python \
    && pip install --upgrade pip \
    && pip install poetry

# Set working directory
WORKDIR /code

# Copy poetry files
COPY pyproject.toml poetry.lock* ./

# Install dependencies
RUN poetry install --no-root --no-interaction --no-ansi

# Copy application code
COPY ./app ./app

# Copy Alembic configuration and migrations
COPY alembic.ini ./
COPY ./alembic ./alembic

# Copy scripts for database initialization
COPY ./scripts ./scripts

# Create uploads directory for image storage
RUN mkdir -p /code/uploads/product_images

# Expose port
EXPOSE 8000

# Run migrations and start the server
CMD ["sh", "-c", "poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000"]
