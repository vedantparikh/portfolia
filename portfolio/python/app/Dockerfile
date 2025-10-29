FROM python:3.12

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

# Install Python dependencies
COPY requirements.txt .
#
# We have REMOVED all the "--no-binary" flags.
# This will be MUCH faster as it downloads pre-compiled wheels.
#
RUN pip install --no-cache-dir -r requirements.txt

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