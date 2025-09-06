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
    
    # Handle base tag for relative URLs (but be careful with existing navigation)
    head = soup.find('head')
    if head:
        # Remove existing base tags that might conflict
        existing_base = head.find('base')
        if existing_base:
            # If there's already a base tag, leave it but make sure it points to target domain through proxy
            current_base = existing_base.get('href', '')
            if current_base and not current_base.startswith(proxy_base):
                if current_base.startswith('http'):
                    # Absolute base URL - convert to proxy
                    parsed_base = urlparse(current_base)
                    if parsed_base.netloc in [parsed_target.netloc, f"www.{parsed_target.netloc}"]:
                        proxy_base_url = f"{proxy_base}{parsed_base.path}"
                        existing_base['href'] = proxy_base_url
                elif current_base.startswith('/'):
                    # Relative base URL - convert to proxy
                    existing_base['href'] = f"{proxy_base}{current_base}"
        else:
            # Only add base tag if there wasn't one originally
            # This prevents breaking sites that don't expect a base tag
            pass
        
    
    # Rewrite common URL attributes
    url_attrs = [
        ('a', 'href'), ('link', 'href'), ('script', 'src'), ('img', 'src'),
        ('form', 'action'), ('iframe', 'src'), ('source', 'src'), 
        ('embed', 'src'), ('object', 'data')
    ]
    
    for tag_name, attr in url_attrs:
        for tag in soup.find_all(tag_name, {attr: True}):
            original_url = tag[attr].strip()
            
            # Skip empty URLs, javascript:, mailto:, tel:, data: URLs
            if not original_url or any(original_url.startswith(prefix) for prefix in ['javascript:', 'mailto:', 'tel:', 'data:', '#']):
                continue
                
            # Convert to absolute URL first
            if original_url.startswith('//'):
                absolute_url = f"{parsed_target.scheme}:{original_url}"
            elif original_url.startswith('/'):
                absolute_url = f"{target_base}{original_url}"
            elif not original_url.startswith(('http://', 'https://')):
                # Handle relative URLs properly
                absolute_url = urljoin(target_url, original_url)
            else:
                absolute_url = original_url
            
            # Parse the absolute URL
            parsed_abs = urlparse(absolute_url)
            
            # Define target domains (main domain and www variant)
            target_domains = [parsed_target.netloc]
            if parsed_target.netloc.startswith('www.'):
                target_domains.append(parsed_target.netloc[4:])  # Remove www.
            else:
                target_domains.append(f"www.{parsed_target.netloc}")  # Add www.
            
            # Always rewrite URLs that belong to the target domain OR have no domain (relative URLs)
            should_rewrite = (
                not parsed_abs.netloc or  # Relative URLs with no domain
                parsed_abs.netloc in target_domains  # Same domain URLs
            )
            
            if should_rewrite:
                proxy_url = f"{proxy_base}{parsed_abs.path}"
                if parsed_abs.query:
                    proxy_url += f"?{parsed_abs.query}"
                if parsed_abs.fragment:
                    proxy_url += f"#{parsed_abs.fragment}"
                
                # Debug logging for URL rewriting
                print(f"REWRITE: {original_url} -> {proxy_url}")
                tag[attr] = proxy_url
            else:
                # Debug: log URLs we're NOT rewriting
                print(f"NOT REWRITING (external domain): {original_url} -> {parsed_abs.netloc}")
    
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

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def catch_all_proxy(request: Request, path: str):
    """Catch-all handler for requests that don't match /proxy/ prefix"""
    if not proxy_config["enabled"] or not proxy_config["target_url"]:
        return Response("Proxy not configured", status_code=503)
    
    # Skip if this is a proxy request (shouldn't happen but safety check)
    if path.startswith("proxy/"):
        return Response("Invalid proxy path", status_code=400)
    
    # Handle requests that don't start with /proxy/ by forwarding to target
    target_url = f"{proxy_config['target_url']}/{path}"
    if request.url.query:
        target_url += f"?{request.url.query}"
    
    logger.info(f"Catch-all proxying: {request.method} {target_url}")
    
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            headers = {k: v for k, v in request.headers.items() if k.lower() != "host"}
            
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=await request.body()
            )
            
            clean_headers = clean_response_headers(dict(response.headers))
            
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=clean_headers
            )
            
    except httpx.RequestError as e:
        logger.error(f"Catch-all proxy error: {e}")
        return Response(f"Resource not found: {path}", status_code=404)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)