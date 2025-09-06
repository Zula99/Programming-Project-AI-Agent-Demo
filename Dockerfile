# AI Agent Demo Factory - Docker Setup
FROM python:3.11-slim

# Set environment variables for UTF-8 support
ENV PYTHONIOENCODING=utf-8
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

# Set working directory
WORKDIR /app

# Install basic system dependencies 
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    unzip \
    xvfb \
    # For crawling and processing
    libxml2-dev \
    libxslt1-dev \
    libffi-dev \
    libssl-dev \
    # Cleanup
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY ai-agent-demo-factory-backend/crawl4ai-agent/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Create Playwright browser cache directory and set environment
RUN mkdir -p /app/.cache/ms-playwright && chmod 777 /app/.cache/ms-playwright
ENV PLAYWRIGHT_BROWSERS_PATH=/app/.cache/ms-playwright

# Install Playwright browsers and system dependencies as root
RUN playwright install chromium
RUN playwright install-deps chromium || echo "Some deps failed but continuing..."

# Copy the application code
COPY ai-agent-demo-factory-backend/ /app/backend/
COPY crawl4ai/ /app/crawl4ai/
COPY CLAUDE.md /app/
# Copy application files
# Note: README.md is optional, build will continue if not found

# Create output directory with proper permissions
RUN mkdir -p /app/output && chmod 777 /app/output

# Set Python path to include our modules
ENV PYTHONPATH=/app/backend:/app/crawl4ai:/app
# Set crawl4ai database path to writable location
ENV CRAWL4AI_BASE_DIRECTORY=/app/output/.crawl4ai

# Create a non-root user for security
RUN groupadd -r aiagent && useradd -r -g aiagent -d /app aiagent
RUN chown -R aiagent:aiagent /app
# Create home directory for crawl4ai database
RUN mkdir -p /home/aiagent && chown -R aiagent:aiagent /home/aiagent
USER aiagent

# Expose proxy port
EXPOSE 8000

# Default working directory for crawl operations
WORKDIR /app/backend/crawl4ai-agent

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; print('AI Agent System Ready'); sys.exit(0)"

# Default command - start proxy server (crawler available via exec)
CMD ["python", "/app/backend/Proxy/proxy_server.py"]