FROM python:3.14

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Set work directory
WORKDIR /app

# Install system dependencies
# We only need libpq-dev (for psycopg2) and curl (for HEALTHCHECK)
# All build tools (gcc, rustc, cargo, etc.) are no longer needed
# because we are using pre-compiled wheels.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.13.6 /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock ./
RUN UV_PROJECT_ENVIRONMENT=/usr/local uv sync --frozen --inexact --no-cache

# Copy project
COPY . .

# Make startup script executable
RUN chmod +x /app/start_api.sh

# Expose port
EXPOSE 8000

# Health check using curl (available in the image)
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# Use startup script
CMD ["/app/start_api.sh"]