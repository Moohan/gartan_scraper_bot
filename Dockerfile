# Multi-stage Docker build for Gartan Scraper Bot
FROM python:3.14-alpine AS builder

# Install build dependencies for Alpine
RUN apk add --no-cache --virtual .build-deps \
    gcc \
    musl-dev \
    linux-headers \
    && apk add --no-cache git

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Clean up build dependencies to reduce layer size
RUN apk del .build-deps

# Production stage - Use same Alpine base for consistency
FROM python:3.14-alpine AS production

# Install runtime dependencies for Alpine
RUN apk add --no-cache \
    sqlite \
    curl \
    ca-certificates

# Create non-root user (Alpine style)
RUN addgroup -g 1000 -S gartan && \
    adduser -u 1000 -S gartan -G gartan

# Set working directory
WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/gartan/.local

# Create directories for data persistence
RUN mkdir -p /app/data /app/_cache /app/logs && \
    chown -R gartan:gartan /app

# Copy application code (do this after creating directories for better caching)
COPY --chown=gartan:gartan *.py ./

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
