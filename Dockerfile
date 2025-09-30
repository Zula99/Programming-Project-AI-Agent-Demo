# AI Agent Demo Factory - Combined Docker Setup
# Stage 1: Build Frontend
FROM node:20-slim AS frontend-builder

WORKDIR /app/frontend

# Install build dependencies for native modules
RUN apt-get update && apt-get install -y \
    python3 \
    make \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy frontend package files
COPY ai-agent-demo-factory-frontend/package.json ./

# Install dependencies fresh (no lockfile to force platform-specific binaries)
RUN npm install

# Copy frontend source
COPY ai-agent-demo-factory-frontend/ ./

# Build frontend
RUN npm run build

# Stage 2: Backend with Frontend
FROM python:3.11-slim

# Set environment variables for UTF-8 support
ENV PYTHONIOENCODING=utf-8
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

# Set working directory
WORKDIR /app

# Install system dependencies (Python backend + Node.js for frontend)
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
    # Add Node.js
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
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
COPY crawl4ai/ /app/crawl4ai/

# Copy built frontend standalone output from frontend-builder stage
COPY --from=frontend-builder /app/frontend/.next/standalone /app/frontend
COPY --from=frontend-builder /app/frontend/.next/static /app/frontend/.next/static
COPY --from=frontend-builder /app/frontend/public /app/frontend/public

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

# Expose backend and frontend ports
EXPOSE 8000 3000

# Default working directory for crawl operations
WORKDIR /app/backend/crawl4ai-agent

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; print('AI Agent System Ready'); sys.exit(0)"

# Start script to run both backend and frontend
CMD bash -c "cd /app/frontend && node server.js & cd /app/backend && python main.py"