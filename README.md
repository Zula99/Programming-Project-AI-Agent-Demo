# AI Agent Demo Factory

A comprehensive web crawling and demo generation platform featuring both Norconnex crawler integration and an intelligent Crawl4AI agent system with interactive UI.

## 🌟 Features

### Norconnex Crawler Interface
- Traditional web crawler with real-time progress tracking
- Data visualization and search functionality
- OpenSearch integration for indexed content

### Crawl4AI Agent Interface (NEW!)
- **Interactive AI Agent** - Real-time conversation with the crawling agent
- **Live WebSocket Updates** - See agent output as it happens
- **User Interaction** - Respond to agent questions with Yes/No buttons or custom text
- **Intelligent Crawling** - AI-powered site analysis and strategy selection
- **Quality Assessment** - Real-time quality scoring and progress monitoring

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Node.js 18+
- npm or yarn

### 1. Start the Backend (FastAPI)

```bash
cd ai-agent-demo-factory-backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

**Backend will be available at:** `http://localhost:8000`

### 2. Start the Frontend (Next.js)

```bash
cd ai-agent-demo-factory-frontend
npm install
npm run dev
```

**Frontend will be available at:** `http://localhost:3000`

## 🎯 How to Use

### Access the Applications

1. **Norconnex Crawler**: `http://localhost:3000/` (homepage)
2. **Crawl4AI Agent**: `http://localhost:3000/crawl4ai` (new feature!)

### Using the Crawl4AI Agent

1. **Navigate** to the Crawl4AI Agent page using the header navigation
2. **Enter a URL** in the input field (e.g., `https://commbank.com.au`)
3. **Click "Start Crawl4AI Agent"** to begin the intelligent crawling process
4. **Watch the live output** in the terminal-style display on the right
5. **Interact with the agent** when it asks questions:
   - Use **Yes/No buttons** for quick responses
   - Use **custom text input** for specific instructions
6. **Monitor progress** as the agent analyzes, crawls, and assesses quality

### Example Agent Interaction Flow

```
🤖 Crawl4AI Agent initialized
📋 Starting site reconnaissance...
🔍 Analyzing https://commbank.com.au
✅ Site type detected: JavaScript-heavy banking site

❓ I've detected this is a banking site that requires special handling.
   Should I proceed with full browser rendering? This will take longer
   but capture dynamic content.

[User clicks "Yes"]

📥 User responded: yes
🚀 Starting full browser crawl...
📄 Crawling / (Homepage)
📄 Crawling /business (Business)
...
❓ Found PDF documents, asking user...

[User responds with custom text or Yes/No]

📄 Including PDF documents
✅ Crawl completed successfully!
📊 Quality Score: 92% (Excellent)
```

## 🏗️ Architecture

### Frontend (Next.js + TypeScript + Tailwind)
- **Pages**:
  - `/` - Norconnex crawler interface
  - `/crawl4ai` - Crawl4AI agent interface
- **Components**: Modular React components with consistent styling
- **API Integration**: WebSocket + REST API communication
- **Real-time Updates**: Live agent output streaming

### Backend (FastAPI + Python)
- **Norconnex Endpoints**: Traditional crawler API (`/crawl`, `/status`, `/results`)
- **Crawl4AI Endpoints**: Agent interaction API (`/crawl4ai/*`)
- **WebSocket Support**: Live bidirectional communication
- **Agent Simulation**: Realistic AI agent behavior with user interaction

### Key Technologies
- **Frontend**: Next.js 15, React 19, TypeScript, Tailwind CSS
- **Backend**: FastAPI, Python, WebSockets, asyncio
- **Icons**: React Icons (Heroicons)
- **Real-time**: WebSocket connections for live updates

## 📁 Project Structure

```
ai-agent-demo-factory/
├── ai-agent-demo-factory-frontend/     # Next.js frontend
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx                # Norconnex crawler page
│   │   │   └── crawl4ai/
│   │   │       └── page.tsx            # Crawl4AI agent page
│   │   ├── components/                 # Reusable React components
│   │   │   ├── Header.tsx              # Navigation header
│   │   │   ├── Crawl4AIUrlBar.tsx      # URL input for agent
│   │   │   ├── AgentOutputCard.tsx     # Live agent output
│   │   │   └── AgentInteractionPanel.tsx # User interaction controls
│   │   └── lib/
│   │       └── crawl4ai-api.ts         # API client functions
├── ai-agent-demo-factory-backend/      # FastAPI backend
│   ├── main.py                         # Main FastAPI application
│   ├── crawl4ai-agent/                 # Crawl4AI agent system
│   └── requirements.txt                # Python dependencies
└── README.md                           # This file
```

## 🔧 Development

### Environment Setup

Create `.env.local` in the frontend directory:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### API Endpoints

#### Norconnex Crawler
- `POST /crawl` - Start traditional crawl
- `GET /status/{run_id}` - Get crawl status
- `GET /results/{run_id}` - Get crawl results

#### Crawl4AI Agent
- `POST /crawl4ai/start` - Start agent session
- `GET /crawl4ai/status/{run_id}` - Get agent status and logs
- `POST /crawl4ai/respond` - Send user response to agent
- `WebSocket /crawl4ai/ws/{run_id}` - Live agent updates

### WebSocket Communication

The Crawl4AI agent uses WebSocket for real-time communication:

```javascript
// Message types from agent
{
  "type": "log",
  "log": {
    "timestamp": "14:30:15",
    "message": "🤖 Agent initialized",
    "type": "info"
  }
}

{
  "type": "status",
  "status": "waiting_for_input",
  "question": "Should I proceed with full browser rendering?"
}
```

## 🎨 UI Features

- **Consistent Design**: Matches existing Norconnex crawler styling
- **Responsive Layout**: Works on desktop and mobile
- **Real-time Feedback**: Live status indicators and progress
- **Interactive Elements**: Buttons, forms, and live terminals
- **Professional Appearance**: Clean, modern interface

## 🚨 Troubleshooting

### Frontend Won't Start
```bash
# Clear Next.js cache
rm -rf .next
rm -rf node_modules/.cache
npm run dev
```

### WebSocket Connection Issues
- Ensure backend is running on port 8000
- Check browser console for connection errors
- Verify CORS settings in FastAPI

### Path Length Issues (Windows)
- Use shorter directory paths
- Consider moving project closer to root drive

## 🔮 Future Enhancements

- **Real Crawl4AI Integration**: Replace simulation with actual Crawl4AI agent
- **Authentication**: User accounts and session management
- **Data Persistence**: Database storage for crawl results
- **Advanced Analytics**: Quality metrics and performance tracking
- **Export Features**: Download crawl data and reports

## 📝 License

This project is part of the AI Agent Demo Factory capstone project.

---

**Happy Crawling! 🕷️✨**