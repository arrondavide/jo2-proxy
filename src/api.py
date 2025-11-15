"""
REST API for Proxy Service - Provides proxies only
"""
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from functools import wraps
import time
from typing import Dict
from . import config
from .proxy_provider import ProxyProvider
from .proxy_manager import ProxyManager
from .database import ProxyDatabase

app = Flask(__name__)
CORS(app)

# Initialize
provider = ProxyProvider()
manager = ProxyManager()
db = ProxyDatabase()

# Simple rate limiting
rate_limit_store = {}


def require_api_key(f):
    """Decorator to require API key"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not config.API_KEY:
            return f(*args, **kwargs)
        
        api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
        if not api_key or api_key != config.API_KEY:
            return jsonify({'error': 'Invalid or missing API key'}), 401
        
        return f(*args, **kwargs)
    return decorated


def rate_limit(f):
    """Simple rate limiting"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not config.RATE_LIMIT_ENABLED:
            return f(*args, **kwargs)
        
        api_key = request.headers.get('X-API-Key', 'default')
        now = time.time()
        minute = int(now / 60)
        key = f"{api_key}:{minute}"
        
        if key not in rate_limit_store:
            rate_limit_store[key] = 0
        
        rate_limit_store[key] += 1
        
        if rate_limit_store[key] > config.RATE_LIMIT_PER_MINUTE:
            return jsonify({
                'error': 'Rate limit exceeded',
                'limit': config.RATE_LIMIT_PER_MINUTE,
                'retry_after': 60 - (now % 60)
            }), 429
        
        return f(*args, **kwargs)
    return decorated


@app.route('/')
def index():
    """API root"""
    return jsonify({
        'service': 'Proxy Service API',
        'version': '1.0.0',
        'description': 'Get working proxies for your projects',
        'endpoints': {
            'get_proxies': '/api/proxies',
            'random_proxy': '/api/proxy/random',
            'health': '/api/health',
            'stats': '/api/stats',
            'refresh': '/api/refresh'
        },
        'documentation': 'See API_DOCS.md'
    })


@app.route('/api/health')
def health():
    """Health check"""
    stats = db.get_stats()
    return jsonify({
        'status': 'healthy',
        'active_proxies': stats['active_proxies'],
        'total_proxies': stats['total_proxies'],
        'timestamp': time.time()
    })


@app.route('/api/proxies', methods=['GET'])
@require_api_key
@rate_limit
def get_proxies():
    """
    Get list of proxies
    
    Query params:
        limit (int): Number of proxies (default: 10, max: 100)
        format (str): Output format ('json', 'text', 'csv', 'url')
        min_success_rate (float): Minimum success rate 0-1 (default: 0.5)
        country (str): Filter by country code (e.g., 'US')
        protocol (str): Filter by protocol ('http', 'https', 'socks4', 'socks5')
    
    Returns:
        Proxy list in requested format
    """
    # Get parameters
    limit = min(request.args.get('limit', type=int, default=10), 100)
    output_format = request.args.get('format', default='json').lower()
    min_rate = request.args.get('min_success_rate', type=float, default=0.5)
    country = request.args.get('country', default=None)
    protocol_filter = request.args.get('protocol', default=None)
    
    # Get proxies
    proxies = provider.get_proxies(
        limit=limit,
        min_success_rate=min_rate,
        country=country,
        protocol=protocol_filter
    )
    
    # Format output
    if output_format == 'json':
        # JSON format with full details
        formatted = []
        for proxy in proxies:
            success = proxy.get('success_count', 0)
            fail = proxy.get('fail_count', 0)
            total = success + fail
            rate = (success / total) if total > 0 else 0
            
            formatted.append({
                'ip': proxy['ip'],
                'port': proxy['port'],
                'protocol': proxy.get('protocol', 'http'),
                'country': proxy.get('country'),
                'success_rate': round(rate, 2),
                'speed': proxy.get('speed'),
                'url': provider.format_proxy_url(proxy)
            })
        
        return jsonify({
            'success': True,
            'count': len(formatted),
            'proxies': formatted
        })
    
    elif output_format in ['text', 'csv', 'url']:
        # Text-based formats
        output = provider.export_proxies(proxies, format=output_format)
        return Response(output, mimetype='text/plain')
    
    else:
        return jsonify({'error': f'Invalid format: {output_format}'}), 400


@app.route('/api/proxy/random', methods=['GET'])
@require_api_key
@rate_limit
def get_random_proxy():
    """
    Get a single random proxy
    
    Query params:
        format (str): Output format ('json', 'text', 'url')
        min_success_rate (float): Minimum success rate 0-1 (default: 0.5)
    
    Returns:
        Single proxy
    """
    output_format = request.args.get('format', default='json').lower()
    min_rate = request.args.get('min_success_rate', type=float, default=0.5)
    
    proxy = provider.get_random_proxy(min_success_rate=min_rate)
    
    if not proxy:
        return jsonify({'error': 'No proxies available'}), 404
    
    if output_format == 'json':
        success = proxy.get('success_count', 0)
        fail = proxy.get('fail_count', 0)
        total = success + fail
        rate = (success / total) if total > 0 else 0
        
        return jsonify({
            'success': True,
            'proxy': {
                'ip': proxy['ip'],
                'port': proxy['port'],
                'protocol': proxy.get('protocol', 'http'),
                'country': proxy.get('country'),
                'success_rate': round(rate, 2),
                'speed': proxy.get('speed'),
                'url': provider.format_proxy_url(proxy)
            }
        })
    
    elif output_format == 'text':
        return Response(provider.format_proxy_simple(proxy), mimetype='text/plain')
    
    elif output_format == 'url':
        return Response(provider.format_proxy_url(proxy), mimetype='text/plain')
    
    else:
        return jsonify({'error': f'Invalid format: {output_format}'}), 400


@app.route('/api/proxies/best', methods=['GET'])
@require_api_key
@rate_limit
def get_best_proxies():
    """Get best performing proxies"""
    limit = min(request.args.get('limit', type=int, default=10), 100)
    output_format = request.args.get('format', default='json').lower()
    
    proxies = provider.get_best_proxies(limit=limit)
    
    if output_format == 'json':
        formatted = []
        for proxy in proxies:
            success = proxy.get('success_count', 0)
            fail = proxy.get('fail_count', 0)
            total = success + fail
            rate = (success / total) if total > 0 else 0
            
            formatted.append({
                'ip': proxy['ip'],
                'port': proxy['port'],
                'protocol': proxy.get('protocol', 'http'),
                'country': proxy.get('country'),
                'success_rate': round(rate, 2),
                'speed': proxy.get('speed'),
                'url': provider.format_proxy_url(proxy)
            })
        
        return jsonify({
            'success': True,
            'count': len(formatted),
            'proxies': formatted
        })
    else:
        output = provider.export_proxies(proxies, format=output_format)
        return Response(output, mimetype='text/plain')


@app.route('/api/stats', methods=['GET'])
@require_api_key
def get_stats():
    """Get service statistics"""
    stats = provider.get_stats()
    return jsonify({
        'success': True,
        'stats': stats
    })


@app.route('/api/refresh', methods=['POST'])
@require_api_key
def refresh():
    """Trigger proxy pool refresh"""
    result = manager.refresh_proxy_pool()
    return jsonify(result)


@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    app.run(
        host=config.API_HOST,
        port=config.API_PORT,
        debug=config.DEBUG
    )