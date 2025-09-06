#!/usr/bin/env python3
"""
Start the Auto-Proxy Server
Run this to enable auto-proxy configuration after crawls complete.
"""
import uvicorn

if __name__ == "__main__":
    print("   Starting Auto-Proxy Server...")
    print("   URL: http://localhost:8000")
    print("   Status: http://localhost:8000/")
    print("   Configure: POST http://localhost:8000/auto-configure")
    print("   Proxy: http://localhost:8000/proxy/[path]")
    print("   Press Ctrl+C to stop")
    print()
    
    uvicorn.run(
        "proxy_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )