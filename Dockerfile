FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN ln -sf /usr/local/bin/python3 /usr/local/bin/python \
    && pip install --upgrade pip \
    && pip install "poetry==1.8.4"

WORKDIR /code

# Copy poetry files
COPY pyproject.toml poetry.lock* ./

# Install deps into the *global* environment, not a venv
RUN poetry config virtualenvs.create false \
    && poetry install --no-root --no-interaction --no-ansi

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

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]