"""
Configuration for Proxy Rotation Service
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Proxy Sources - Free public proxy lists
PROXY_SOURCES = [
    'https://api.proxyscrape.com/v2/?request=get&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all',
    'https://www.proxy-list.download/api/v1/get?type=http',
    'https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt',
    'https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt',
    'https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt',
    'https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-http.txt',
    'https://raw.githubusercontent.com/mmpx12/proxy-list/master/http.txt',
    'https://raw.githubusercontent.com/roosterkid/openproxylist/main/HTTPS_RAW.txt',
]

# Proxy Settings
MIN_PROXIES = 10  # Lower minimum requirement
MAX_PROXIES = 5000  # Store more proxies
VALIDATION_TIMEOUT = 10  # Give proxies more time (doubled from 5 to 10)
REFRESH_INTERVAL = 3600  # Refresh proxy pool every hour (seconds)
VALIDATION_URL = 'https://httpbin.org/ip'  # URL to test proxies

# Rotation Settings
ROTATION_STRATEGY = 'random'  # Options: 'random', 'round_robin', 'weighted'
MAX_RETRIES = 3  # Maximum retry attempts per request
REQUEST_TIMEOUT = 10  # Default timeout for requests

# Database
DATABASE_PATH = os.getenv('DATABASE_PATH', 'proxies.db')

# API Settings (for SaaS mode)
API_HOST = os.getenv('API_HOST', '0.0.0.0')
API_PORT = int(os.getenv('API_PORT', 5000))
API_KEY = os.getenv('API_KEY', None)  # Set for authentication
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

# Rate Limiting (for SaaS)
RATE_LIMIT_ENABLED = os.getenv('RATE_LIMIT_ENABLED', 'False').lower() == 'true'
RATE_LIMIT_PER_MINUTE = int(os.getenv('RATE_LIMIT_PER_MINUTE', 60))

# Logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.getenv('LOG_FILE', 'proxy_service.log')

# User Agents for rotation
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
]