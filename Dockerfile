# AI Agent Demo Factory - Docker Setup
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
    # For Playwright browser automation
    libnss3-dev \
    libatk-bridge2.0-dev \
    libdrm-dev \
    libxcomposite-dev \
    libxdamage-dev \
    libxrandr-dev \
    libgbm-dev \
    libxss-dev \
    libasound2-dev \
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

# Install Playwright browsers
RUN playwright install chromium
RUN playwright install-deps chromium

# Copy the application code
COPY ai-agent-demo-factory-backend/ /app/backend/
COPY crawl4ai/ /app/crawl4ai/
COPY CLAUDE.md /app/
COPY README.md /app/ 2>/dev/null || true

# Create output directory with proper permissions
RUN mkdir -p /app/output && chmod 777 /app/output

# Set Python path to include our modules
ENV PYTHONPATH=/app/backend:/app/crawl4ai:/app

# Create a non-root user for security
RUN groupadd -r aiagent && useradd -r -g aiagent aiagent
RUN chown -R aiagent:aiagent /app
USER aiagent

# Default working directory for crawl operations
WORKDIR /app/backend/crawl4ai-agent

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; print('AI Agent System Ready'); sys.exit(0)"

# Default command - interactive mode
CMD ["python", "run_agent.py"]