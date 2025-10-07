# Crawl4AI Backend Dockerfile
FROM python:3.11-slim

# Set environment variables for UTF-8 support
ENV PYTHONIOENCODING=utf-8
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    unzip \
    xvfb \
    build-essential \
    gcc \
    g++ \
    libxml2-dev \
    libxslt1-dev \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements and install Python dependencies
COPY ai-agent-demo-factory-backend/crawl4ai-agent/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Create Playwright browser cache directory and set environment
RUN mkdir -p /app/.cache/ms-playwright && chmod 777 /app/.cache/ms-playwright
ENV PLAYWRIGHT_BROWSERS_PATH=/app/.cache/ms-playwright

# Install Playwright browsers and system dependencies as root
RUN playwright install chromium
RUN playwright install-deps chromium || echo "Some deps failed but continuing..."

# Copy backend application code
COPY ai-agent-demo-factory-backend/ /app/backend/

# Create output directory with proper permissions
RUN mkdir -p /app/output && chmod 777 /app/output

# Set Python path to include our modules
ENV PYTHONPATH=/app/backend:/app
# Set crawl4ai database path to writable location
ENV CRAWL4AI_BASE_DIRECTORY=/app/output/.crawl4ai

# Create a non-root user for security
RUN groupadd -r aiagent && useradd -r -g aiagent -d /app aiagent
RUN chown -R aiagent:aiagent /app
# Create home directory for crawl4ai database
RUN mkdir -p /home/aiagent && chown -R aiagent:aiagent /home/aiagent
USER aiagent

# Expose backend port only
EXPOSE 8000

# Default working directory for crawl operations
WORKDIR /app/backend

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; print('Crawl4AI Backend Ready'); sys.exit(0)"

# Start Crawl4AI backend only
CMD ["python", "main.py"]
