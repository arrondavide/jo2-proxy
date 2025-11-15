"""
Proxy Service - Provides working proxies
"""

__version__ = '1.0.0'

from .proxy_provider import ProxyProvider, get_proxies, get_random_proxy
from .proxy_manager import ProxyManager
from .database import ProxyDatabase

__all__ = [
    'ProxyProvider',
    'ProxyManager',
    'ProxyDatabase',
    'get_proxies',
    'get_random_proxy'
]