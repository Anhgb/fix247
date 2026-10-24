FROM python:3.11-slim

WORKDIR /app

# Install system deps for psycopg2 / PostGIS
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

# Install pip & hatch
RUN pip install --no-cache-dir hatch

# Copy dependency files first for layer caching
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e ".[dev]"

# Copy source
COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
