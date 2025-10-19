AI AGENT DEMO FACTORY - README
===============================================

TEAM: RMIT Team BLUE
GROUP: AA-661A

PROJECT OVERVIEW
----------------
An intelligent web crawling and demo generation platform featuring dual crawling engines,
AI-powered content classification, real-time proxy serving, and comprehensive search capabilities.

GITHUB REPOSITORY
-----------------
https://github.com/Zula99/Programming-Project-AI-Agent-Demo.git

DEPLOYED APPLICATION
--------------------
Local development: http://localhost:3000 (Frontend), http://localhost:8000 (Backend)
Deployed URL: [Insert deployment URL if applicable, or state "Not deployed"]

QUICK START
-----------

1. Prerequisites:
   - Docker Desktop installed
   - 8GB+ RAM recommended
   - Ports available: 3000, 5000, 8000, 9200, 5601

2. Installation & Running:

   # Navigate to project directory
   cd "RMIT Team BLUE - AI Agent Demo Factory"

   # Start all services with Docker Compose
   docker-compose up -d

   # Verify services are running
   docker-compose ps

3. Access the Application:
   - Frontend UI: http://localhost:3000
   - Backend API (Norconex): http://localhost:5000
   - Backend API (Crawl4AI): http://localhost:8000
   - OpenSearch: http://localhost:9200

4. Stop Services:
   docker-compose down

TESTING THE APPLICATION
------------------------

Quick Test:
1. Open http://localhost:3000
2. Enter a test URL (e.g., https://books.toscrape.com)
3. Click "Start Crawl"
4. Monitor real-time progress
5. Search the crawled content

DETAILED DOCUMENTATION
----------------------

For comprehensive documentation, see:

1. Norconex_README.md
   - Full Norconex crawler guide
   - API reference
   - WebSocket implementation
   - Troubleshooting

2. ai-agent-demo-factory-backend/CRAWL4AI_SYSTEM_DOCUMENTATION.md
   - Complete Crawl4AI system architecture
   - AI classification details
   - Module reference
   - Integration guides

3. Database Credentials: See data.txt

RELEASE NOTES
-------------

Version 1.0.0 (Final Submission)
- Dual crawling systems: Norconex + Crawl4AI
- AI-powered content classification with GPT-3.5-turbo
- Real-time WebSocket progress streaming
- OpenSearch integration with 98+ field schema
- Dynamic proxy serving with search injection
- Intelligent quality monitoring and plateau detection
- Site type detection and adaptive strategies
- Comprehensive Search365 schema support

TROUBLESHOOTING
---------------

If services won't start:
  docker-compose down
  docker-compose up -d

Check logs:
  docker-compose logs -f

For detailed troubleshooting, see Norconex_README.md and CRAWL4AI_SYSTEM_DOCUMENTATION.md

SUPPORT
-------
Refer to detailed documentation files for complete guides and troubleshooting.
