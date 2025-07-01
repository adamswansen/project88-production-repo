FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash project88
RUN chown -R project88:project88 /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .
RUN chown -R project88:project88 /app

# Create log directory
RUN mkdir -p /var/log/project88 && chown -R project88:project88 /var/log/project88

# Switch to non-root user
USER project88

# Health check
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import psycopg2; psycopg2.connect('$DB_CONNECTION_STRING')" || exit 1

# Default command
CMD ["python", "main.py", "--workers", "2"] 