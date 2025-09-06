from fastapi import FastAPI, Request
from fastapi.responses import Response, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import logging
import asyncio
from typing import Optional
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, urlparse

# Initialize FastAPI app for proxy
app = FastAPI(title="Auto-Proxy Server")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    "crawl_completed": False
}

class ProxyConfig(BaseModel):
    target_url: str
    run_id: Optional[str] = None
    enabled: bool = True

@app.get("/")
async def proxy_status():
    return {
        "message": "Auto-Proxy Server", 
        "target_url": proxy_config["target_url"],
        "enabled": proxy_config["enabled"],
        "run_id": proxy_config["run_id"],
        "crawl_completed": proxy_config["crawl_completed"]
    }

@app.post("/auto-configure")
async def auto_configure_from_crawl(config: ProxyConfig):
    """Auto-configure proxy when crawl completes"""
    proxy_config["target_url"] = config.target_url.rstrip("/")
    proxy_config["run_id"] = config.run_id
    proxy_config["enabled"] = config.enabled
    proxy_config["crawl_completed"] = True
    
    logger.info(f"Auto-proxy configured from crawl - Target: {proxy_config['target_url']}, Run ID: {config.run_id}")
    return {
        "message": "Auto-proxy configured from crawl completion",
        "proxy_url": f"http://localhost:8000/proxy/",
        "config": proxy_config
    }

@app.get("/config")
async def get_proxy_config():
    """Get current proxy configuration"""
    return proxy_config

def rewrite_urls_in_html(html_content: str, target_url: str, proxy_base: str = "http://localhost:8000/proxy") -> str:
    """Rewrite URLs in HTML to work through proxy"""
    soup = BeautifulSoup(html_content, 'html.parser')
    parsed_target = urlparse(target_url)
    target_base = f"{parsed_target.scheme}://{parsed_target.netloc}"
    
    # Add base tag for relative URLs
    head = soup.find('head')
    if head:
        # Remove existing base tags
        for base_tag in head.find_all('base'):
            base_tag.decompose()
        # Add proxy base tag
        base_tag = soup.new_tag('base', href=f"{proxy_base}/")
        head.insert(0, base_tag)
        
    
    # Rewrite common URL attributes
    url_attrs = [
        ('a', 'href'), ('link', 'href'), ('script', 'src'), ('img', 'src'),
        ('form', 'action'), ('iframe', 'src'), ('source', 'src'), 
        ('embed', 'src'), ('object', 'data')
    ]
    
    for tag_name, attr in url_attrs:
        for tag in soup.find_all(tag_name, {attr: True}):
            original_url = tag[attr]
            
            # Skip javascript:, mailto:, tel:, data: URLs
            if any(original_url.startswith(prefix) for prefix in ['javascript:', 'mailto:', 'tel:', 'data:', '#']):
                continue
                
            # Convert to absolute URL first
            if original_url.startswith('//'):
                absolute_url = f"{parsed_target.scheme}:{original_url}"
            elif original_url.startswith('/'):
                absolute_url = f"{target_base}{original_url}"
            elif not original_url.startswith(('http://', 'https://')):
                absolute_url = urljoin(target_url, original_url)
            else:
                absolute_url = original_url
            
            # Rewrite to proxy URL if it's from the same domain (including www variants)
            parsed_abs = urlparse(absolute_url)
            target_domains = [parsed_target.netloc, f"www.{parsed_target.netloc}"]
            if parsed_target.netloc.startswith('www.'):
                target_domains.append(parsed_target.netloc[4:])  # Remove www.
            
            if parsed_abs.netloc in target_domains:
                proxy_url = f"{proxy_base}{parsed_abs.path}"
                if parsed_abs.query:
                    proxy_url += f"?{parsed_abs.query}"
                if parsed_abs.fragment:
                    proxy_url += f"#{parsed_abs.fragment}"
                
                # Debug logging for URL rewriting
                print(f"REWRITE: {original_url} -> {proxy_url}")
                tag[attr] = proxy_url
    
    return str(soup)

def rewrite_urls_in_css(css_content: str, target_url: str, proxy_base: str = "http://localhost:8000/proxy") -> str:
    """Rewrite URLs in CSS to work through proxy"""
    parsed_target = urlparse(target_url)
    target_base = f"{parsed_target.scheme}://{parsed_target.netloc}"
    
    # Pattern to match url() in CSS
    url_pattern = r'url\s*\(\s*["\']?([^"\')\s]+)["\']?\s*\)'
    
    def replace_css_url(match):
        original_url = match.group(1)
        
        # Skip data URLs
        if original_url.startswith('data:'):
            return match.group(0)
        
        # Convert to absolute URL
        if original_url.startswith('//'):
            absolute_url = f"{parsed_target.scheme}:{original_url}"
        elif original_url.startswith('/'):
            absolute_url = f"{target_base}{original_url}"
        elif not original_url.startswith(('http://', 'https://')):
            absolute_url = urljoin(target_url, original_url)
        else:
            absolute_url = original_url
        
        # Rewrite to proxy URL if same domain
        parsed_abs = urlparse(absolute_url)
        if parsed_abs.netloc == parsed_target.netloc:
            proxy_url = f"{proxy_base}{parsed_abs.path}"
            if parsed_abs.query:
                proxy_url += f"?{parsed_abs.query}"
            return f'url("{proxy_url}")'
        
        return match.group(0)
    
    return re.sub(url_pattern, replace_css_url, css_content)

def clean_response_headers(headers: dict) -> dict:
    """Clean headers for proxy response"""
    # Remove problematic headers
    cleaned = {k: v for k, v in headers.items() if k.lower() not in [
        'content-encoding', 'transfer-encoding', 'content-length',
        'content-security-policy', 'x-frame-options', 
        'strict-transport-security'
    ]}
    
    # Add CORS headers
    cleaned.update({
        'access-control-allow-origin': '*',
        'access-control-allow-methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'access-control-allow-headers': '*',
    })
    
    return cleaned

@app.api_route("/proxy/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_request(request: Request, path: str):
    """Proxy all requests to the configured target site with URL rewriting"""
    
    if not proxy_config["enabled"] or not proxy_config["target_url"]:
        return Response("Proxy not configured or disabled", status_code=503)
    
    # Build target URL
    target_url = f"{proxy_config['target_url']}/{path}"
    if request.url.query:
        target_url += f"?{request.url.query}"
    
    logger.info(f"Proxying: {request.method} {target_url}")
    
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            # Prepare headers - remove host header to avoid conflicts
            headers = {k: v for k, v in request.headers.items() if k.lower() != "host"}
            
            # Forward the request
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=await request.body()
            )
            
            # Clean headers
            clean_headers = clean_response_headers(dict(response.headers))
            
            # Get content type
            content_type = response.headers.get("content-type", "").lower()
            
            # Rewrite URLs for HTML and CSS content
            if "text/html" in content_type:
                try:
                    rewritten_content = rewrite_urls_in_html(
                        response.text, 
                        proxy_config["target_url"]
                    )
                    logger.info(f"Rewrote HTML content for {target_url}")
                    return HTMLResponse(
                        content=rewritten_content,
                        status_code=response.status_code,
                        headers=clean_headers
                    )
                except Exception as e:
                    logger.warning(f"HTML rewriting failed: {e}")
                    # Fall back to original content
            
            elif "text/css" in content_type:
                try:
                    rewritten_content = rewrite_urls_in_css(
                        response.text,
                        proxy_config["target_url"]
                    )
                    return Response(
                        content=rewritten_content,
                        status_code=response.status_code,
                        headers=clean_headers,
                        media_type="text/css"
                    )
                except Exception as e:
                    logger.warning(f"CSS rewriting failed: {e}")
                    # Fall back to original content
            
            # For all other content types, return as-is
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=clean_headers
            )
            
    except httpx.RequestError as e:
        logger.error(f"Proxy error: {e}")
        return Response(f"Proxy error: {str(e)}", status_code=502)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)