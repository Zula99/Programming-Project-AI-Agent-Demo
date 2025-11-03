#!/usr/bin/env python3
"""
Auto-Proxy Server - Main Application
Refactored for maintainability - all components split into focused modules
"""
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import Response, HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict
from urllib.parse import urlparse
from pathlib import Path
import logging
import sys
import os
from dotenv import load_dotenv

# Configure logging first
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)
logger.info(f"Loading .env from: {env_path}")
logger.info(f"API Key loaded: {bool(os.getenv('OPENAI_API_KEY'))}")

# Add Utility directory to path for OpenSearch integration
sys.path.insert(0, str(Path(__file__).parent.parent / "Utility"))

# Import OpenSearch integration
try:
    from opensearch_integration import Crawl4AIOpenSearchIntegration, OpenSearchConfig
    OPENSEARCH_AVAILABLE = True
except ImportError:
    OPENSEARCH_AVAILABLE = False
    logger.warning("OpenSearch integration not available")

# Import our refactored modules
from Proxy.proxy_handler import proxy_request_handler, catch_all_proxy_handler
from Proxy.template_manager import clear_template_cache

# Initialize FastAPI app for proxy
app = FastAPI(title="Auto-Proxy Server")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Proxy configuration - will be set when crawl completes
proxy_config = {
    "target_url": None,
    "enabled": False,
    "run_id": None,
    "crawl_completed": False,
    "search_injection_enabled": True
}

# OpenSearch integration for search injection
opensearch_integration = None
opensearch_index_name = None


def initialize_opensearch(domain: str = None, run_id: str = None, host: str = "opensearch", port: int = 9200):
    """Initialize OpenSearch integration for search injection"""
    global opensearch_integration, opensearch_index_name

    if not OPENSEARCH_AVAILABLE:
        logger.warning("OpenSearch not available - search injection disabled")
        return False

    try:
        config = OpenSearchConfig(host=host, port=port, scheme="http")
        opensearch_integration = Crawl4AIOpenSearchIntegration(config)

        # Generate index name from domain and run_id (must match indexing_routes.py format)
        if domain and run_id:
            domain_clean = domain.replace(".", "_")
            opensearch_index_name = f"demo-{domain_clean}-{run_id}"

        logger.info(f"OpenSearch initialized for search injection - Index: {opensearch_index_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize OpenSearch: {e}")
        return False


class ProxyConfig(BaseModel):
    target_url: str
    run_id: Optional[str] = None
    enabled: bool = True


@app.post("/auto-configure")
async def auto_configure_from_crawl(config: ProxyConfig):
    """Auto-configure proxy when crawl completes"""
    # Ensure target URL has protocol
    target_url = config.target_url.rstrip("/")
    if not target_url.startswith(("http://", "https://")):
        target_url = f"https://{target_url}"

    # Normalize URL to use www. prefix if the site redirects to it
    # This prevents 301 redirects for every asset request
    parsed = urlparse(target_url)
    if not parsed.netloc.startswith("www.") and parsed.netloc.count(".") >= 1:
        # Try to fetch the base URL and see if it redirects to www
        try:
            import httpx
            with httpx.Client(follow_redirects=False, timeout=5.0) as client:
                response = client.get(target_url)
                if response.status_code in (301, 302, 307, 308):
                    redirect_location = response.headers.get("location", "")
                    if redirect_location.startswith("http"):
                        redirect_parsed = urlparse(redirect_location)
                        if redirect_parsed.netloc.startswith("www."):
                            # Use the www version
                            target_url = f"{parsed.scheme}://www.{parsed.netloc}{parsed.path}"
                            logger.info(f"Normalized target URL to: {target_url}")
        except Exception as e:
            logger.warning(f"Could not check for www redirect: {e}")

    proxy_config["target_url"] = target_url
    proxy_config["run_id"] = config.run_id
    proxy_config["enabled"] = config.enabled
    proxy_config["crawl_completed"] = True

    # Initialize OpenSearch for search injection
    domain = urlparse(target_url).netloc
    opensearch_initialized = initialize_opensearch(domain, config.run_id)

    logger.info(f"Auto-proxy configured from crawl - Target: {proxy_config['target_url']}, Run ID: {config.run_id}")
    if opensearch_initialized:
        logger.info(f"OpenSearch search injection enabled for {domain}")

    return {
        "message": "Auto-proxy configured from crawl completion",
        "proxy_url": f"http://localhost:8000/proxy/",
        "config": proxy_config,
        "search_injection": opensearch_initialized,
        "opensearch_index": opensearch_index_name
    }


@app.get("/config")
async def get_proxy_config():
    """Get current proxy configuration"""
    return proxy_config


@app.post("/clear-template-cache")
async def clear_template_cache_endpoint():
    """Clear the search template cache to force fresh template generation"""
    cache_count = clear_template_cache()
    return {
        "message": f"Cleared {cache_count} cached templates",
        "cache_cleared": True
    }


@app.api_route("/proxy/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_request(request: Request, path: str):
    """Proxy all requests to the configured target site with URL rewriting"""
    return await proxy_request_handler(
        request=request,
        path=path,
        proxy_config=proxy_config,
        opensearch_integration=opensearch_integration,
        opensearch_index_name=opensearch_index_name
    )


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def catch_all_proxy(request: Request, path: str):
    """Catch-all handler for requests that don't match /proxy/ prefix"""
    return await catch_all_proxy_handler(
        request=request,
        path=path,
        proxy_config=proxy_config,
        opensearch_integration=opensearch_integration,
        opensearch_index_name=opensearch_index_name
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
