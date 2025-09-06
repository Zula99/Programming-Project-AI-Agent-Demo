#!/bin/bash
# Docker Run Examples for AI Agent Demo Factory with Proxy System
# Replaces static mirroring with dynamic proxy for better performance

echo "AI Agent Demo Factory - Proxy System Examples"
echo "================================================"

# Build the image
echo "Building Docker image..."
docker build -t ai-agent-demo .

echo ""
echo "Ready! Choose your deployment method:"
echo ""

echo "1. Start System (Recommended - Proxy Auto-Starts)"
echo "   docker-compose up -d"
echo "   # Proxy automatically starts on port 8000"
echo "   # Access: http://localhost:8000/"
echo ""

echo "2. Run Crawler (After Step 1)"
echo "   docker-compose exec ai-agent-demo python run_agent.py"
echo "   # Auto-configures the running proxy when crawl completes"
echo "   # Demo site: http://localhost:8000/proxy/"
echo ""

echo "3. Run Multiple Crawls"
echo "   # Proxy stays running, just run more crawls:"
echo "   docker-compose exec ai-agent-demo python run_agent.py"
echo "   # Each successful crawl reconfigures the proxy"
echo ""

echo "4. Quick Test Sites"
echo "   # Example.com (simple)"
echo "   curl -X POST http://localhost:8000/auto-configure \\"
echo "     -H \"Content-Type: application/json\" \\"
echo "     -d '{\"target_url\": \"https://example.com\", \"enabled\": true}'"
echo "   # Visit: http://localhost:8000/proxy/"
echo ""

echo "5. Check System Status"
echo "   curl http://localhost:8000/          # Proxy status"
echo "   curl http://localhost:8000/config    # Current configuration"
echo "   # Demo site: http://localhost:8000/proxy/"
echo ""

echo "New Proxy System Benefits:"
echo "- Dynamic site serving (no static file generation)"
echo "- Real-time URL rewriting for perfect styling"
echo "- Universal CORS handling"
echo "- Ready for search bar injection"
echo "- Same port 8000 as before (seamless replacement)"
echo ""

echo "Migration from Static Mirroring:"
echo "- OLD: Crawl -> Generate static files -> Serve on :8000"
echo "- NEW: Crawl -> Auto-configure proxy -> Live proxy on :8000"
echo "- Same end result, better performance and flexibility!"
echo ""

echo "To stop everything:"
echo "   docker-compose down"