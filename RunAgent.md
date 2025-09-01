# Running SmartMirrorAgent with Docker

## Quick Start

1. **Make sure Docker Desktop is running**

2. **Run the agent:**
   ```bash
   docker-compose run --rm --service-ports ai-agent-demo
   ```

3. **Enter a website when prompted:**
   ```
   Enter target website (e.g., nab.com.au, example.com): nab.com.au
   ```

4. **Watch it crawl, build the mirror, and automatically serve it**

5. **Access the mirror in your browser at:**
   ```
   http://localhost:8000/agent_crawls/[domain]/
   ```
   Example: `http://localhost:8000/agent_crawls/example.com/`

## What it does

- Crawls the website with full JavaScript rendering
- Creates a static mirror for offline browsing
- Saves everything to `./ai-agent-demo-factory-backend/crawl4ai-agent/output/`
- Shows quality metrics when complete
- Automatically starts web server on port 8000
- Serves the mirror immediately for viewing

## Alternative Commands

```bash
# Build and run in one step
docker-compose up --build

# Then connect to running container
docker exec -it smart-mirror-agent bash
python run_agent.py
```

## Workflow

1. Agent crawls the website
2. Creates static mirror with all assets
3. Shows quality metrics and crawl summary
4. Automatically starts HTTP server on port 8000
5. Mirror is immediately viewable at `http://localhost:8000/agent_crawls/[domain]/`
6. Press Ctrl+C to stop server when done

## Output Location

Results are also saved locally to:
```
./ai-agent-demo-factory-backend/crawl4ai-agent/output/agent_crawls/[domain]/
```

## Troubleshooting

If you get browser errors, rebuild:
```bash
docker-compose down
docker-compose up --build
```

**Note:** The `--service-ports` flag is essential to access the mirror server. Without it, port 8000 won't be accessible from your host browser.

## Viewing the Mirror

After the agent completes:
1. Agent automatically starts web server on port 8000
2. Open browser and go to: `http://localhost:8000/agent_crawls/[domain]/`
3. Browse the offline mirror with all assets localized
4. Press Ctrl+C in terminal to stop server when done