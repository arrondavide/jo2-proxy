"""
Proxy Provider - Provides proxies to users
"""
import random
from typing import List, Dict, Optional
from . import config
from .proxy_manager import ProxyManager


class ProxyProvider:
    """Provides working proxies to users"""
    
    def __init__(self):
        self.manager = ProxyManager()
    
    def get_proxies(self, limit: int = 10, min_success_rate: float = 0.5, 
                    country: str = None, protocol: str = None) -> List[Dict]:
        """
        Get list of working proxies
        
        Args:
            limit: Number of proxies to return
            min_success_rate: Minimum success rate (0-1)
            country: Filter by country code (e.g., 'US')
            protocol: Filter by protocol ('http', 'https', 'socks4', 'socks5')
        
        Returns:
            List of proxy dictionaries
        """
        proxies = self.manager.get_proxy_pool(limit=limit * 2, min_success_rate=min_success_rate)
        
        # Filter by country if specified
        if country:
            proxies = [p for p in proxies if p.get('country', '').upper() == country.upper()]
        
        # Filter by protocol if specified
        if protocol:
            proxies = [p for p in proxies if p.get('protocol', '').lower() == protocol.lower()]
        
        # Return requested number
        return proxies[:limit]
    
    def get_random_proxy(self, min_success_rate: float = 0.5) -> Optional[Dict]:
        """
        Get a single random proxy
        
        Args:
            min_success_rate: Minimum success rate (0-1)
        
        Returns:
            Proxy dictionary or None
        """
        proxies = self.get_proxies(limit=50, min_success_rate=min_success_rate)
        if proxies:
            return random.choice(proxies)
        return None
    
    def get_best_proxies(self, limit: int = 10) -> List[Dict]:
        """
        Get the best performing proxies
        
        Args:
            limit: Number of proxies to return
        
        Returns:
            List of best proxies sorted by success rate and speed
        """
        return self.get_proxies(limit=limit, min_success_rate=0.7)
    
    def format_proxy_url(self, proxy: Dict) -> str:
        """
        Format proxy as URL string
        
        Args:
            proxy: Proxy dictionary
        
        Returns:
            Proxy URL string (e.g., 'http://1.2.3.4:8080')
        """
        return f"{proxy['protocol']}://{proxy['ip']}:{proxy['port']}"
    
    def format_proxy_simple(self, proxy: Dict) -> str:
        """
        Format proxy as simple string
        
        Args:
            proxy: Proxy dictionary
        
        Returns:
            Simple proxy string (e.g., '1.2.3.4:8080')
        """
        return f"{proxy['ip']}:{proxy['port']}"
    
    def export_proxies(self, proxies: List[Dict], format: str = 'text') -> str:
        """
        Export proxies in different formats
        
        Args:
            proxies: List of proxy dictionaries
            format: Output format ('text', 'json', 'csv', 'url')
        
        Returns:
            Formatted string
        """
        if format == 'text' or format == 'simple':
            # Simple format: IP:PORT per line
            return '\n'.join([self.format_proxy_simple(p) for p in proxies])
        
        elif format == 'url':
            # URL format: protocol://IP:PORT per line
            return '\n'.join([self.format_proxy_url(p) for p in proxies])
        
        elif format == 'csv':
            # CSV format
            lines = ['ip,port,protocol,country,success_rate,speed']
            for p in proxies:
                success = p.get('success_count', 0)
                fail = p.get('fail_count', 0)
                total = success + fail
                rate = (success / total * 100) if total > 0 else 0
                speed = p.get('speed', 0) or 0
                
                lines.append(f"{p['ip']},{p['port']},{p.get('protocol', 'http')},"
                           f"{p.get('country', '')}," f"{rate:.1f},{speed:.2f}")
            return '\n'.join(lines)
        
        elif format == 'json':
            # JSON format (will be handled by API)
            return proxies
        
        else:
            # Default to simple text
            return '\n'.join([self.format_proxy_simple(p) for p in proxies])
    
    def get_stats(self) -> Dict:
        """Get proxy pool statistics"""
        return self.manager.db.get_stats()
    
    def refresh_proxies(self) -> Dict:
        """Refresh the proxy pool"""
        return self.manager.refresh_proxy_pool()


# Convenience functions
def get_proxies(limit: int = 10, **kwargs) -> List[Dict]:
    """Quick function to get proxies"""
    provider = ProxyProvider()
    return provider.get_proxies(limit=limit, **kwargs)


def get_random_proxy(**kwargs) -> Optional[Dict]:
    """Quick function to get random proxy"""
    provider = ProxyProvider()
    return provider.get_random_proxy(**kwargs)