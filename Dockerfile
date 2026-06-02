# ============================================================================
# Hydra Trading System — Dockerfile
# ============================================================================
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose ports
EXPOSE 8788 8501

# Default: run FastAPI server
CMD ["uvicorn", "backend.signal_server:app", "--host", "0.0.0.0", "--port", "8788"]
