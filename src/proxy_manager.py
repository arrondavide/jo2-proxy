"""
Proxy Manager - Fetches and validates proxies from multiple sources
"""
import requests
import time
import random
import concurrent.futures
from typing import List, Dict, Optional
from urllib.parse import urlparse
from datetime import datetime
from . import config
from .database import ProxyDatabase


class ProxyManager:
    """Manages proxy fetching, validation, and storage"""
    
    def __init__(self):
        self.db = ProxyDatabase()
        self.sources = config.PROXY_SOURCES
        self.validation_url = config.VALIDATION_URL
        self.timeout = config.VALIDATION_TIMEOUT
    
    def fetch_proxies_from_source(self, source_url: str) -> List[str]:
        """Fetch proxy list from a single source"""
        try:
            print(f"Fetching proxies from: {source_url}")
            response = requests.get(source_url, timeout=10)
            
            if response.status_code == 200:
                # Parse text response - most sources return IP:PORT per line
                proxies = []
                for line in response.text.split('\n'):
                    line = line.strip()
                    if ':' in line and not line.startswith('#'):
                        proxies.append(line)
                
                print(f"Found {len(proxies)} proxies from {source_url}")
                return proxies
            
        except Exception as e:
            print(f"Error fetching from {source_url}: {e}")
        
        return []
    
    def fetch_all_proxies(self) -> List[str]:
        """Fetch proxies from all configured sources"""
        all_proxies = []
        
        # Use ThreadPoolExecutor for parallel fetching
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(self.fetch_proxies_from_source, source) 
                      for source in self.sources]
            
            for future in concurrent.futures.as_completed(futures):
                try:
                    proxies = future.result()
                    all_proxies.extend(proxies)
                except Exception as e:
                    print(f"Error in fetch thread: {e}")
        
        # Remove duplicates
        all_proxies = list(set(all_proxies))
        print(f"Total unique proxies fetched: {len(all_proxies)}")
        
        return all_proxies
    
    def parse_proxy_string(self, proxy_str: str) -> Optional[Dict]:
        """Parse proxy string (IP:PORT) into dict"""
        try:
            if '://' in proxy_str:
                # Format: http://IP:PORT
                parsed = urlparse(proxy_str)
                ip = parsed.hostname
                port = parsed.port
                protocol = parsed.scheme
            else:
                # Format: IP:PORT
                parts = proxy_str.split(':')
                if len(parts) != 2:
                    return None
                ip = parts[0].strip()
                port = int(parts[1].strip())
                protocol = 'http'
            
            return {
                'ip': ip,
                'port': port,
                'protocol': protocol
            }
        except Exception:
            return None
    
    def validate_proxy(self, proxy_dict: Dict) -> bool:
        """Test if a proxy works"""
        proxy_str = f"{proxy_dict['protocol']}://{proxy_dict['ip']}:{proxy_dict['port']}"
        proxies = {
            'http': proxy_str,
            'https': proxy_str
        }
        
        try:
            start_time = time.time()
            response = requests.get(
                self.validation_url,
                proxies=proxies,
                timeout=self.timeout,
                headers={'User-Agent': random.choice(config.USER_AGENTS)}
            )
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                # Update success in database
                self.db.update_proxy_success(
                    proxy_dict['ip'], 
                    proxy_dict['port'],
                    response_time
                )
                return True
            
        except Exception:
            pass
        
        # Mark as failed
        self.db.update_proxy_failure(proxy_dict['ip'], proxy_dict['port'])
        return False
    
    def validate_proxies_batch(self, proxy_list: List[str], max_workers: int = 20) -> int:
        """Validate multiple proxies in parallel"""
        print(f"Validating {len(proxy_list)} proxies...")
        
        # Parse proxy strings
        parsed_proxies = []
        for proxy_str in proxy_list:
            parsed = self.parse_proxy_string(proxy_str)
            if parsed:
                parsed_proxies.append(parsed)
        
        # Add to database first (unvalidated)
        added = self.db.add_proxies_bulk(parsed_proxies)
        print(f"Added {added} new proxies to database")
        
        # Validate in parallel
        valid_count = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(self.validate_proxy, proxy): proxy 
                      for proxy in parsed_proxies[:100]}  # Validate first 100 to save time
            
            for future in concurrent.futures.as_completed(futures):
                try:
                    if future.result():
                        valid_count += 1
                        if valid_count % 10 == 0:
                            print(f"Validated: {valid_count} working proxies")
                except Exception:
                    pass
        
        print(f"Validation complete: {valid_count} working proxies")
        return valid_count
    
    def refresh_proxy_pool(self) -> Dict:
        """Main method: Fetch, validate, and store proxies"""
        print("=" * 60)
        print("Starting proxy pool refresh...")
        print("=" * 60)
        
        start_time = time.time()
        
        # Step 1: Fetch from all sources
        all_proxies = self.fetch_all_proxies()
        
        if not all_proxies:
            print("Warning: No proxies fetched from any source!")
            return {
                'success': False,
                'message': 'No proxies fetched',
                'stats': self.db.get_stats()
            }
        
        # Step 2: Validate proxies
        valid_count = self.validate_proxies_batch(all_proxies)
        
        # Step 3: Clean up old dead proxies
        removed = self.db.remove_inactive_proxies(days=7)
        print(f"Removed {removed} inactive proxies")
        
        # Get final stats
        stats = self.db.get_stats()
        elapsed = time.time() - start_time
        
        print("=" * 60)
        print(f"Refresh complete in {elapsed:.2f} seconds")
        print(f"Active proxies: {stats['active_proxies']}")
        print(f"Total in database: {stats['total_proxies']}")
        print("=" * 60)
        
        return {
            'success': True,
            'valid_proxies': valid_count,
            'elapsed_time': elapsed,
            'stats': stats
        }
    
    def get_proxy_pool(self, limit: int = None, min_success_rate: float = 0.5) -> List[Dict]:
        """Get list of working proxies"""
        proxies = self.db.get_active_proxies(limit=limit, min_success_rate=min_success_rate)
        
        # If pool is too small, refresh
        if len(proxies) < config.MIN_PROXIES:
            print(f"Proxy pool too small ({len(proxies)}), refreshing...")
            self.refresh_proxy_pool()
            proxies = self.db.get_active_proxies(limit=limit, min_success_rate=min_success_rate)
        
        return proxies
    
    def get_random_proxy(self) -> Optional[Dict]:
        """Get a random working proxy"""
        proxies = self.get_proxy_pool(limit=50)
        if proxies:
            return random.choice(proxies)
        return None
    
    def format_proxy_for_requests(self, proxy_dict: Dict) -> Dict:
        """Format proxy dict for requests library"""
        proxy_url = f"{proxy_dict['protocol']}://{proxy_dict['ip']}:{proxy_dict['port']}"
        return {
            'http': proxy_url,
            'https': proxy_url
        }