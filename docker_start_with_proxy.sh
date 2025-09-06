#!/bin/bash
# Start AI Agent Demo Factory with Proxy Server
# This replaces the need for static mirroring

echo "   Starting AI Agent Demo Factory with Proxy..."
echo "   Proxy will be available at: http://localhost:8000/"
echo "   After crawling, demo site at: http://localhost:8000/proxy/"
echo

# Start Docker container with proxy service
docker-compose up -d

# Give it a moment to start
sleep 3

# Start proxy server inside the container
echo "  Starting proxy server inside container..."
docker-compose exec ai-agent-demo python /app/backend/start_services.py &

echo "  Services started!"
echo
echo "   Next Steps:"
echo "   1. Run crawler: docker-compose exec ai-agent-demo python run_agent.py"
echo "   2. Visit demo: http://localhost:8000/proxy/"
echo "   3. Check status: http://localhost:8000/"
echo
echo "  To stop: docker-compose down"