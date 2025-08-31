# Docker Setup Guide - AI Agent Demo Factory

## Quick Start

### Prerequisites
- **Docker Desktop** installed and running
- **Git** for cloning the repository
- **8GB+ RAM** recommended for browser automation

### One-Line Deployment
```bash
# Clone and run
git clone <repository-url>
cd Programming-Project-AI-Agent-Demo
docker-compose up --build
```

### Usage
```bash
# Interactive crawling session
docker-compose exec ai-agent-demo python run_agent.py

# Or get a shell inside the container
docker-compose exec ai-agent-demo bash
```

## Detailed Setup

### 1. Build the Docker Image
```bash
# Build the image
docker-compose build

# Or build manually
docker build -t smart-mirror-agent .
```

### 2. Run the Container
```bash
# Start with docker-compose (recommended)
docker-compose up -d

# Or run manually
docker run -it \
  -v $(pwd)/output:/app/output \
  -e PYTHONIOENCODING=utf-8 \
  smart-mirror-agent
```

### 3. Test the Setup
```bash
# Test with CommBank (this should now work!)
docker-compose exec ai-agent-demo python run_agent.py
# Enter: commbank.com.au
```

## Key Benefits

###  **Fixes Windows Issues**
- **UTF-8 encoding** by default - no more charmap codec errors
- **No path length limits** - Windows filesystem restrictions eliminated
- **Consistent environment** - same behavior across all operating systems

###  **Browser Automation Ready**
- **Playwright + Chromium** pre-installed and configured
- **Headless browsing** optimized for server environments
- **JavaScript rendering** works reliably

###  **Developer Friendly**
- **Volume mounts** for live code editing
- **Persistent output** - crawled data saved to host
- **Easy debugging** - interactive shell access

## Container Architecture

```
/app/
├── backend/           # AI agent code
│   └── crawl4ai-agent/
├── crawl4ai/          # Crawling utilities
├── output/            # Persistent storage (mounted)
├── CLAUDE.md          # Documentation
└── requirements.txt
```

## Environment Variables

```yaml
# Required for UTF-8 support
PYTHONIOENCODING: utf-8
LANG: C.UTF-8
LC_ALL: C.UTF-8

# Optional: AI API keys (for future AI integration)
# OPENAI_API_KEY: your_key_here
# ANTHROPIC_API_KEY: your_key_here
```

## Volume Mounts

| Host Path | Container Path | Purpose |
|-----------|----------------|---------|
| `./output` | `/app/output` | Persistent crawl results |
| `./ai-agent-demo-factory-backend` | `/app/backend` | Live code editing |
| `./crawl4ai` | `/app/crawl4ai` | Utility functions |

## Common Commands

### Development Commands
```bash
# Build and start
docker-compose up --build

# Rebuild after code changes
docker-compose build --no-cache

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Crawling Commands
```bash
# Interactive mode
docker-compose exec ai-agent-demo python run_agent.py

# Direct crawling
docker-compose exec ai-agent-demo python -c "
from smart_mirror_agent import SmartMirrorAgent
agent = SmartMirrorAgent()
agent.process_url('commbank.com.au')
"

# Check crawl results
docker-compose exec ai-agent-demo ls -la /app/output/
```

### Debugging Commands
```bash
# Shell access
docker-compose exec ai-agent-demo bash

# Check Python environment
docker-compose exec ai-agent-demo python --version
docker-compose exec ai-agent-demo pip list

# Test UTF-8 support
docker-compose exec ai-agent-demo python -c "print('UTF-8 test: → ← ↑ ↓ " " ' ' © ®')"
```

## Troubleshooting

### Container Won't Start
```bash
# Check Docker is running
docker --version
docker-compose --version

# View build logs
docker-compose build --no-cache --progress=plain

# Check system resources
docker system df
docker system prune  # Clean up if needed
```

### Permission Issues
```bash
# Fix output directory permissions
sudo chown -R $USER:$USER ./output
chmod -R 755 ./output
```

### Browser Issues
```bash
# Test browser installation
docker-compose exec ai-agent-demo python -c "
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch()
    print('Browser test: OK')
    browser.close()
"
```

### Memory Issues
```bash
# Increase Docker memory allocation in Docker Desktop
# Recommended: 8GB+ for complex sites with JavaScript rendering
```

## Performance Optimization

### Resource Limits
```yaml
# Add to docker-compose.yml service
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 4G
    reservations:
      memory: 2G
```

### Caching
```dockerfile
# Dockerfile already optimized with:
# - Multi-stage builds for smaller image size
# - Dependency installation before code copy
# - Proper layer caching
```

## Security

### Non-Root User
- Container runs as `aiagent` user (non-root)
- Proper file permissions set
- Minimal attack surface

### Network Isolation
- Custom Docker network
- Only necessary ports exposed
- No privileged access required

## Integration with CI/CD

### GitHub Actions Example
```yaml
name: Test Docker Deployment
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build and test
        run: |
          docker-compose build
          docker-compose run ai-agent-demo python -c "print('Deployment test: OK')"
```

## Next Steps

Once Docker is working:
1. **Test CommBank crawling** - should work without encoding errors
2. **Add AI API integration** - uncomment API key environment variables
3. **Implement learning database** - uncomment PostgreSQL service
4. **Add web interface** - use exposed port 8080

## Support

If you encounter issues:
1. Check the troubleshooting section above
2. Verify Docker Desktop is running and has sufficient resources
3. Try `docker-compose down && docker-compose up --build --force-recreate`
4. Create an issue with your error logs