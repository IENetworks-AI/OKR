FROM python:3.11-slim

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl build-essential && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

# Expose Flask port
EXPOSE 5001

ENV FLASK_ENV=production

CMD ["python", "api/app.py", "--host", "0.0.0.0", "--port", "5001"]

