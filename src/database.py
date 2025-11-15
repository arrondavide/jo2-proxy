"""
Database module for storing and managing proxies
"""
import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional
from contextlib import contextmanager
from . import config


class ProxyDatabase:
    """Manages proxy storage in SQLite"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or config.DATABASE_PATH
        self._init_database()
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _init_database(self):
        """Initialize database schema"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Proxies table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS proxies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ip TEXT NOT NULL,
                    port INTEGER NOT NULL,
                    protocol TEXT DEFAULT 'http',
                    country TEXT,
                    anonymity TEXT,
                    speed REAL,
                    success_count INTEGER DEFAULT 0,
                    fail_count INTEGER DEFAULT 0,
                    last_checked TIMESTAMP,
                    last_used TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(ip, port)
                )
            ''')
            
            # Index for faster queries
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_active_proxies 
                ON proxies(is_active, success_count)
            ''')
            
            # Usage statistics table (for SaaS)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS usage_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    api_key TEXT,
                    endpoint TEXT,
                    proxy_used TEXT,
                    success BOOLEAN,
                    response_time REAL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
    
    def add_proxy(self, ip: str, port: int, protocol: str = 'http', 
                  country: str = None, anonymity: str = None) -> bool:
        """Add a new proxy to the database"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR IGNORE INTO proxies 
                    (ip, port, protocol, country, anonymity, last_checked)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (ip, port, protocol, country, anonymity, datetime.now()))
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Error adding proxy {ip}:{port}: {e}")
            return False
    
    def add_proxies_bulk(self, proxies: List[Dict]) -> int:
        """Add multiple proxies at once"""
        added = 0
        with self.get_connection() as conn:
            cursor = conn.cursor()
            for proxy in proxies:
                try:
                    cursor.execute('''
                        INSERT OR IGNORE INTO proxies 
                        (ip, port, protocol, country, anonymity, last_checked)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        proxy.get('ip'),
                        proxy.get('port'),
                        proxy.get('protocol', 'http'),
                        proxy.get('country'),
                        proxy.get('anonymity'),
                        datetime.now()
                    ))
                    if cursor.rowcount > 0:
                        added += 1
                except Exception:
                    continue
        return added
    
    def get_active_proxies(self, limit: int = None, min_success_rate: float = 0.0) -> List[Dict]:
        """Get list of active proxies"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = '''
                SELECT ip, port, protocol, country, anonymity, 
                       success_count, fail_count, last_used, speed
                FROM proxies 
                WHERE is_active = 1
                AND (success_count + fail_count = 0 OR 
                     CAST(success_count AS FLOAT) / (success_count + fail_count) >= ?)
                ORDER BY success_count DESC, fail_count ASC
            '''
            
            if limit:
                query += f' LIMIT {limit}'
            
            cursor.execute(query, (min_success_rate,))
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]
    
    def update_proxy_success(self, ip: str, port: int, response_time: float = None):
        """Mark proxy as successful"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE proxies 
                SET success_count = success_count + 1,
                    last_used = ?,
                    speed = ?,
                    is_active = 1
                WHERE ip = ? AND port = ?
            ''', (datetime.now(), response_time, ip, port))
    
    def update_proxy_failure(self, ip: str, port: int):
        """Mark proxy as failed"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Increment fail count
            cursor.execute('''
                UPDATE proxies 
                SET fail_count = fail_count + 1,
                    last_checked = ?
                WHERE ip = ? AND port = ?
            ''', (datetime.now(), ip, port))
            
            # Deactivate if fail rate is too high
            cursor.execute('''
                UPDATE proxies 
                SET is_active = 0
                WHERE ip = ? AND port = ?
                AND fail_count > 5
                AND (success_count = 0 OR 
                     CAST(fail_count AS FLOAT) / (success_count + fail_count) > 0.7)
            ''', (ip, port))
    
    def remove_inactive_proxies(self, days: int = 7) -> int:
        """Remove proxies that haven't worked in X days"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM proxies 
                WHERE is_active = 0 
                AND last_checked < datetime('now', '-' || ? || ' days')
            ''', (days,))
            return cursor.rowcount
    
    def get_stats(self) -> Dict:
        """Get database statistics"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) as total FROM proxies')
            total = cursor.fetchone()['total']
            
            cursor.execute('SELECT COUNT(*) as active FROM proxies WHERE is_active = 1')
            active = cursor.fetchone()['active']
            
            cursor.execute('''
                SELECT AVG(CAST(success_count AS FLOAT) / (success_count + fail_count)) as avg_success_rate
                FROM proxies 
                WHERE (success_count + fail_count) > 0
            ''')
            avg_rate = cursor.fetchone()['avg_success_rate'] or 0
            
            return {
                'total_proxies': total,
                'active_proxies': active,
                'inactive_proxies': total - active,
                'average_success_rate': round(avg_rate * 100, 2)
            }
    
    def log_usage(self, api_key: str, endpoint: str, proxy_used: str, 
                  success: bool, response_time: float):
        """Log API usage (for SaaS analytics)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO usage_stats 
                (api_key, endpoint, proxy_used, success, response_time)
                VALUES (?, ?, ?, ?, ?)
            ''', (api_key, endpoint, proxy_used, success, response_time))