#!/usr/bin/env python3
"""
Run the Proxy Service API Server
"""
import sys
from src.api import app
from src import config

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 Starting Proxy Service API")
    print("=" * 60)
    print(f"Host: {config.API_HOST}")
    print(f"Port: {config.API_PORT}")
    print(f"Debug: {config.DEBUG}")
    
    if config.API_KEY:
        print(f"Authentication: ENABLED")
    else:
        print(f"Authentication: DISABLED")
        print("⚠️  Set API_KEY in .env for production")
    
    print("=" * 60)
    print("\nEndpoints:")
    print(f"  Get Proxies:    http://localhost:{config.API_PORT}/api/proxies")
    print(f"  Random Proxy:   http://localhost:{config.API_PORT}/api/proxy/random")
    print(f"  Best Proxies:   http://localhost:{config.API_PORT}/api/proxies/best")
    print(f"  Health Check:   http://localhost:{config.API_PORT}/api/health")
    print(f"  Statistics:     http://localhost:{config.API_PORT}/api/stats")
    print(f"  Refresh:        http://localhost:{config.API_PORT}/api/refresh")
    print("=" * 60 + "\n")
    
    try:
        app.run(
            host=config.API_HOST,
            port=config.API_PORT,
            debug=config.DEBUG
        )
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped")
        sys.exit(0)