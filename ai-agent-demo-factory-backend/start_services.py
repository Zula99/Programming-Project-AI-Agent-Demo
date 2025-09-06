#!/usr/bin/env python3
"""
Startup script for AI Agent Demo Factory
Starts both the proxy server and provides access to crawler functionality
"""
import sys
import subprocess
import signal
import time
from pathlib import Path
import threading

def start_proxy_server():
    """Start the proxy server in background"""
    try:
        print(" Starting Proxy Server on port 8000...")
        proxy_path = Path(__file__).parent / "Proxy" / "proxy_server.py"
        
        # Start proxy server
        proxy_process = subprocess.Popen([
            sys.executable, str(proxy_path)
        ], cwd=proxy_path.parent)
        
        return proxy_process
        
    except Exception as e:
        print(f" Failed to start proxy server: {e}")
        return None

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    print("\n Shutting down services...")
    sys.exit(0)

def main():
    """Main startup function"""
    print("=" * 60)
    print(" AI Agent Demo Factory - Service Startup")
    print("=" * 60)
    print(" Starting services...")
    print()
    
    # Handle shutdown signals
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start proxy server
    proxy_process = start_proxy_server()
    if not proxy_process:
        print(" Failed to start proxy server")
        return 1
    
    # Wait a moment for proxy to start
    time.sleep(2)
    
    print("   Services started successfully!")
    print()
    print("   Access Points:")
    print("   Proxy Status: http://localhost:8000/")
    print("   Demo Site: http://localhost:8000/proxy/ (after crawl)")
    print()
    print("   Available Commands:")
    print("   Crawler: python crawl4ai-agent/run_agent.py")
    print("   Configure Proxy: curl -X POST http://localhost:8000/auto-configure ...")
    print()
    print("Press Ctrl+C to stop all services")
    print("=" * 60)
    
    try:
        # Keep the main process alive
        while True:
            # Check if proxy is still running
            if proxy_process.poll() is not None:
                print(" Proxy server stopped unexpectedly")
                break
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n Shutdown requested...")
    finally:
        # Clean shutdown
        if proxy_process and proxy_process.poll() is None:
            print(" Stopping proxy server...")
            proxy_process.terminate()
            proxy_process.wait()
        
        print(" All services stopped")
        return 0

if __name__ == "__main__":
    sys.exit(main())