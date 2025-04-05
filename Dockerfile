# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for PostgreSQL
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create necessary directories
RUN mkdir -p uploads generated logs migrations/versions

# Set environment variables
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV FLASK_CONFIG=cloud_run
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8080

# First check that the service can start, then run migrations, then start Gunicorn
CMD gunicorn --bind 0.0.0.0:8080 app:app 