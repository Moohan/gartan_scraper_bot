# Multi-stage Docker build for Gartan Scraper Bot
FROM python:3.13-alpine AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.13-slim AS production

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    sqlite3 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r gartan && useradd --no-log-init -r -g gartan gartan

# Set working directory
WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/gartan/.local

# Copy application code
COPY . .

# Create directories for data persistence
RUN mkdir -p /app/data /app/_cache /app/logs && \
    chown -R gartan:gartan /app

# Set environment variables
ENV PATH=/home/gartan/.local/bin:$PATH
ENV PYTHONPATH=/app
ENV FLASK_ENV=production
ENV PORT=5000

# Switch to non-root user
USER gartan

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Default command
CMD ["python", "container_main.py"]
