"""
Session and connection management optimizations for Gartan Scraper Bot.

Provides persistent HTTP session management and database connection pooling
to improve performance and reduce resource overhead.
"""

import sqlite3
import threading
import requests
from typing import Optional, Dict, Any
import time
from datetime import datetime
from contextlib import contextmanager
from logging_config import get_logger

logger = get_logger()

class SessionManager:
    """Manages persistent HTTP sessions with automatic session reuse and cleanup."""
    
    def __init__(self):
        self._session = None
        self._session_lock = threading.Lock()
        self._last_used = None
        self._session_timeout = 3600  # 1 hour timeout
    
    def get_session(self) -> requests.Session:
        """Get a reusable session, creating new one if expired or missing."""
        with self._session_lock:
            now = time.time()
            
            # Create new session if none exists or expired
            if (self._session is None or 
                self._last_used is None or 
                (now - self._last_used) > self._session_timeout):
                
                if self._session:
                    logger.debug("Closing expired HTTP session")
                    self._session.close()
                
                logger.debug("Creating new persistent HTTP session")
                self._session = requests.Session()
                
                # Set session-wide configuration
                self._session.headers.update({
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                })
                
                # Configure connection pooling
                adapter = requests.adapters.HTTPAdapter(
                    pool_connections=10,
                    pool_maxsize=20,
                    max_retries=3,
                    pool_block=False
                )
                self._session.mount('http://', adapter)
                self._session.mount('https://', adapter)
            
            self._last_used = now
            return self._session
    
    def close(self):
        """Explicitly close the session."""
        with self._session_lock:
            if self._session:
                logger.debug("Closing persistent HTTP session")
                try:
                    self._session.close()
                except AttributeError:
                    # Handle mock sessions in tests that don't have close()
                    pass
                self._session = None
                self._last_used = None

class DatabasePool:
    """Database connection pool for SQLite with connection reuse."""
    
    def __init__(self, db_path: str, max_connections: int = 5):
        self.db_path = db_path
        self.max_connections = max_connections
        self._connections = []
        self._in_use = set()
        self._lock = threading.Lock()
        
        # Configure SQLite for better performance
        self._sqlite_pragma = [
            "PRAGMA journal_mode=WAL",  # Write-Ahead Logging for better concurrency
            "PRAGMA synchronous=NORMAL",  # Faster writes with good durability
            "PRAGMA cache_size=10000",  # 10MB cache
            "PRAGMA temp_store=MEMORY",  # Store temp tables in memory
            "PRAGMA foreign_keys=ON",  # Enable foreign key constraints
        ]
    
    def _create_connection(self) -> sqlite3.Connection:
        """Create a new optimized database connection."""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        
        # Apply performance optimizations
        cursor = conn.cursor()
        for pragma in self._sqlite_pragma:
            cursor.execute(pragma)
        cursor.close()
        
        logger.debug(f"Created new database connection to {self.db_path}")
        return conn
    
    @contextmanager
    def get_connection(self):
        """Context manager to get a database connection from the pool."""
        conn = None
        try:
            with self._lock:
                # Try to reuse an existing connection
                if self._connections:
                    conn = self._connections.pop()
                    self._in_use.add(id(conn))
                else:
                    # Create new connection if pool is empty and under limit
                    if len(self._in_use) < self.max_connections:
                        conn = self._create_connection()
                        self._in_use.add(id(conn))
            
            if conn is None:
                # Pool exhausted, create temporary connection
                logger.debug("Connection pool exhausted, creating temporary connection")
                conn = self._create_connection()
                temp_connection = True
            else:
                temp_connection = False
            
            yield conn
            
        finally:
            if conn:
                if temp_connection:
                    # Close temporary connections immediately
                    conn.close()
                    logger.debug("Closed temporary database connection")
                else:
                    # Return to pool
                    with self._lock:
                        self._in_use.discard(id(conn))
                        if len(self._connections) < self.max_connections:
                            self._connections.append(conn)
                        else:
                            # Pool is full, close connection
                            conn.close()
                            logger.debug("Connection pool full, closed excess connection")
    
    def close_all(self):
        """Close all connections in the pool."""
        with self._lock:
            for conn in self._connections:
                conn.close()
            self._connections.clear()
            self._in_use.clear()
            logger.debug("Closed all database connections in pool")

# Global instances
_session_manager = SessionManager()
_db_pool = None

def get_session_manager() -> SessionManager:
    """Get the global session manager instance."""
    return _session_manager

def get_database_pool(db_path: str = "gartan_availability.db") -> DatabasePool:
    """Get the global database pool instance."""
    global _db_pool
    if _db_pool is None or _db_pool.db_path != db_path:
        if _db_pool:
            _db_pool.close_all()
        _db_pool = DatabasePool(db_path)
        logger.debug(f"Initialized database pool for {db_path}")
    return _db_pool

def close_all_connections():
    """Close all global connections and pools."""
    _session_manager.close()
    if _db_pool:
        _db_pool.close_all()
    logger.debug("Closed all global connections")

# Register cleanup on exit
import atexit
atexit.register(close_all_connections)
