#!/bin/bash
# Docker Run Examples for AI Agent Demo Factory
# Fixes Windows encoding issues with containerized deployment

echo "🐳 AI Agent Demo Factory - Docker Examples"
echo "=========================================="

# Build the image
echo "Building Docker image..."
docker build -t ai-agent-demo .

echo ""
echo "✅ Ready! Choose your deployment method:"
echo ""

echo "1. 📦 Docker Compose (Recommended)"
echo "   docker-compose up -d"
echo "   docker-compose exec ai-agent-demo python -c \"print('UTF-8 test: → ← ↑ ↓ © ®')\""
echo ""

echo "2. 🏃 Quick Crawl Test"
echo "   docker run --rm -v \"\${PWD}/ai-agent-demo-factory-backend/crawl4ai-agent/output:/app/backend/crawl4ai-agent/output\" ai-agent-demo python -c \""
echo "   import asyncio"
echo "   from smart_mirror_agent import SmartMirrorAgent"
echo "   async def test():"
echo "       agent = SmartMirrorAgent()"
echo "       success, metrics, mirror_path = await agent.process_url('https://example.com')"
echo "       print(f'Success: {success}, Quality: {metrics.overall_score}')"
echo "   asyncio.run(test())\""
echo ""

echo "3. 🔍 Interactive Shell"
echo "   docker run --rm -it -v \"\${PWD}/ai-agent-demo-factory-backend/crawl4ai-agent/output:/app/backend/crawl4ai-agent/output\" ai-agent-demo bash"
echo ""

echo "4. 🌐 Crawl Specific Site"
echo "   # CommBank (Unicode-heavy test)"
echo "   docker-compose up -d"
echo "   docker-compose exec ai-agent-demo python run_agent.py"
echo "   # Enter: https://www.commbank.com.au"
echo ""

echo "5. 📊 Check Results"
echo "   ls -la ai-agent-demo-factory-backend/crawl4ai-agent/output/"
echo "   # View generated mirror sites"
echo ""

echo "💡 Pro Tips:"
echo "- All Unicode characters now work perfectly ✅"
echo "- No more Windows path length limits ✅" 
echo "- Consistent UTF-8 encoding across all operations ✅"
echo "- Generated mirrors saved to ./ai-agent-demo-factory-backend/crawl4ai-agent/output/"