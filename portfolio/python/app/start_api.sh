#!/bin/bash

# Portfolia API Startup Script
# This script will start the API with automatic database initialization and migrations

set -e  # Exit on error

echo "🚀 Starting Portfolia API..."

# Wait for postgres to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
max_retries=30
retry_count=0
while ! python -c "import psycopg2; psycopg2.connect(host='${POSTGRES_HOST}', port='${POSTGRES_PORT}', user='${POSTGRES_USER}', password='${POSTGRES_PASSWORD}', dbname='${POSTGRES_DB}')" 2>/dev/null; do
    retry_count=$((retry_count+1))
    if [ $retry_count -ge $max_retries ]; then
        echo "❌ PostgreSQL did not become ready in time"
        exit 1
    fi
    echo "Waiting for PostgreSQL... (attempt $retry_count/$max_retries)"
    sleep 2
done
echo "✅ PostgreSQL is ready!"

# Wait for Redis to be ready
echo "⏳ Waiting for Redis to be ready..."
retry_count=0
while ! python -c "import redis; redis.Redis(host='${REDIS_HOST}', port='${REDIS_PORT}', db='${REDIS_DB}').ping()" 2>/dev/null; do
    retry_count=$((retry_count+1))
    if [ $retry_count -ge $max_retries ]; then
        echo "❌ Redis did not become ready in time"
        exit 1
    fi
    echo "Waiting for Redis... (attempt $retry_count/$max_retries)"
    sleep 2
done
echo "✅ Redis is ready!"

# Run Alembic migrations
echo "🔄 Running database migrations..."
cd /app
alembic upgrade head
if [ $? -eq 0 ]; then
    echo "✅ Database migrations completed successfully!"
else
    echo "❌ Database migrations failed!"
    exit 1
fi

# Start the API with automatic database initialization
echo "🌐 Starting API server..."
python start_api.py
