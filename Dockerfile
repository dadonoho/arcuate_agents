FROM python:3.12-slim

WORKDIR /app

# Install system deps for chromadb
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Copy source
COPY src/ src/
COPY scripts/ scripts/

# Data directories (Railway volume mounts here)
RUN mkdir -p /app/data
ENV CHROMA_PERSIST_DIR=/app/data/chroma_data
ENV SQLITE_DB_PATH=/app/data/chief_of_staff.db

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "chief_of_staff.main:app", "--host", "0.0.0.0", "--port", "8000"]
