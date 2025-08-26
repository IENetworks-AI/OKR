FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    gcc \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements
COPY apps/api/requirements.txt /app/requirements.txt

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

# Copy the entire project
COPY . /app

# Create necessary directories
RUN mkdir -p /app/data/raw /app/data/processed /app/data/final /app/data/models /app/logs

# Set proper permissions
RUN chmod -R 755 /app

# Expose API port
EXPOSE 5001

# Set environment variables
ENV FLASK_ENV=production
ENV FLASK_APP=apps/api/app.py
ENV PYTHONPATH=/app:/app/src
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5001/health || exit 1

# Use gunicorn for production
WORKDIR /app
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "--workers", "2", "--worker-class", "sync", "--timeout", "120", "--keep-alive", "5", "--max-requests", "1000", "--max-requests-jitter", "100", "apps.api.app:app"]