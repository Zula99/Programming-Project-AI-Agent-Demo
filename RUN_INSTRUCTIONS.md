# AI Agent Demo Factory - Complete Setup Instructions

This guide provides exact commands to run the frontend and backend together so the crawl4ai interface works properly.

## Prerequisites

- Node.js (v18 or higher)
- Python 3.11
- Git

## Quick Start (Recommended)

### Step 1: Install Backend Dependencies

```bash
cd ai-agent-demo-factory-backend
pip install -r crawl4ai-agent/requirements.txt
```

### Step 2: Install Frontend Dependencies

```bash
cd ai-agent-demo-factory-frontend
npm install
npm install express http-proxy-middleware cors
```

### Step 3: Start Backend Server

Open **Terminal 1** and run:

```bash
cd ai-agent-demo-factory-backend
python main.py
```

You should see:
```
Starting AI Agent Demo Factory Backend on port 8000...
Crawl4AI endpoints available at:
  POST /crawl4ai/start
  GET /crawl4ai/status/{run_id}
  WebSocket /crawl4ai/ws/{run_id}
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### Step 4: Start Proxy Server

Open **Terminal 2** and run:

```bash
cd ai-agent-demo-factory-frontend
node proxy-server.js
```

### Step 5: Start Frontend Server

Open **Terminal 3** and run:

```bash
cd ai-agent-demo-factory-frontend
npm run dev
```

You should see:
```
   ▲ Next.js 14.x.x
   - Local:        http://localhost:3000 (or 3001, 3002, etc. if 3000 is busy)
   - Ready in Xs
```

### Step 6: Access the Application

1. Open your browser
2. Go to the URL shown in your terminal + `/crawl4ai`
   - If on port 3000: **http://localhost:3000/crawl4ai**
   - If on port 3006: **http://localhost:3006/crawl4ai**
   - Use whatever port Next.js shows you
3. Enter a website URL (e.g., `nab.com.au`, `example.com`)
4. Click "Start Crawl"
5. Watch real-time progress and logs!

## Testing the Integration

### Test 1: Simple Website
- URL: `example.com`
- Expected: Quick crawl with basic content

### Test 2: Banking Website
- URL: `nab.com.au`
- Expected: AI detects banking site, uses full browser strategy

### Test 3: Complex JS Site
- URL: `commbank.com.au`
- Expected: JavaScript rendering, longer crawl time

## What You Should See

### Frontend Interface:
- ✅ URL input bar
- ✅ Real-time progress bar with percentage
- ✅ Live crawl statistics (pages crawled, speed, time remaining)
- ✅ Agent output logs with timestamps
- ✅ Backend logs dropdown (showing server activity)
- ✅ WebSocket connection status indicator

### Backend Logs:
- ✅ SmartMirrorAgent initialization
- ✅ Site reconnaissance and strategy selection
- ✅ Real-time crawl progress
- ✅ AI content classification decisions
- ✅ Quality metrics and completion status

## Troubleshooting

### Backend Won't Start
```bash
# Check if port 8000 is in use
netstat -an | findstr :8000

# If in use, kill the process or change port in main.py
```

### Frontend Can't Connect to Backend
1. Verify backend is running on http://localhost:8000
2. Check browser console for connection errors
3. Ensure no firewall blocking port 8000

### Missing Dependencies
```bash
# Backend missing packages
cd ai-agent-demo-factory-backend
pip install fastapi uvicorn websockets

# Frontend missing packages
cd ai-agent-demo-factory-frontend
npm install
```

### Crawl Fails
- Check backend terminal for error details
- Verify internet connection
- Try a simpler website like `example.com` first

## Advanced Configuration

### Environment Variables

Create `.env` file in backend directory:
```bash
# Optional: Add OpenAI API key for enhanced AI features
OPENAI_API_KEY=your_api_key_here

# Optional: Customize crawl settings
CRAWL4AI_MAX_PAGES=50
CRAWL4AI_REQUEST_DELAY=1.0
```

### Custom Frontend API URL

If running backend on different port, update:
```bash
# ai-agent-demo-factory-frontend/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Docker Alternative (If Fixed)

Once Docker build issues are resolved:

```bash
# Build and start containers
docker-compose up -d --build

# Access directly
docker-compose exec ai-agent-demo python main.py

# View logs
docker logs smart-mirror-agent
```

## File Structure Overview

```
Programming-Project-AI-Agent-Demo/
├── ai-agent-demo-factory-backend/
│   ├── main.py                 # ← FastAPI server (runs on port 8000)
│   ├── crawl4ai-agent/         # ← SmartMirrorAgent implementation
│   └── requirements.txt        # ← Python dependencies
├── ai-agent-demo-factory-frontend/
│   ├── src/app/crawl4ai/       # ← Crawl4AI interface page
│   ├── src/lib/crawl4ai-api.ts # ← API client (connects to port 8000)
│   └── package.json            # ← Node.js dependencies
└── RUN_INSTRUCTIONS.md         # ← This file
```

## Success Indicators

When everything works correctly:

1. **Backend Terminal**: Shows uvicorn server running + crawl logs
2. **Frontend Page**: Shows connected status + real-time updates
3. **Browser Network Tab**: WebSocket connection established
4. **Crawl Output**: Progress bar updates + log messages appear
5. **Agent Behavior**: AI makes intelligent crawling decisions

## Support

If you encounter issues:
1. Check both terminal outputs for error messages
2. Verify all dependencies are installed
3. Ensure no other services using ports 3000 or 8000
4. Try restarting both servers

---

**Happy Crawling! 🕷️🤖**