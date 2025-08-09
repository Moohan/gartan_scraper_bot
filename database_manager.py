"""
Enhanced Database Manager for Gartan Scraper Bot

This module provides centralized database management with:
- Connection pooling
- Transaction management
- Migration system
- Consistent error handling
"""

import sqlite3
import logging
from typing import Dict, List, Any, Optional, Union, Generator
from datetime import datetime, timedelta
from contextlib import contextmanager
from pathlib import Path
import threading
from connection_manager import get_database_pool, get_connection

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Centralized database manager with connection pooling and transaction support."""
    
    def __init__(self, db_path: str = "gartan_availability.db"):
        self.db_path = db_path
        self._lock = threading.Lock()
        
    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Get a database connection with automatic cleanup."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    @contextmanager
    def transaction(self) -> Generator[sqlite3.Connection, None, None]:
        """Get a database connection with transaction management."""
        with self.get_connection() as conn:
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
    
    def ensure_schema(self) -> None:
        """Ensure database schema exists without dropping existing data."""
        schema_version = self._get_schema_version()
        
        if schema_version == 0:
            self._create_initial_schema()
        else:
            self._migrate_schema(schema_version)
    
    def _get_schema_version(self) -> int:
        """Get current schema version."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='schema_version'
                """)
                
                if not cursor.fetchone():
                    return 0
                
                cursor.execute("SELECT version FROM schema_version ORDER BY id DESC LIMIT 1")
                result = cursor.fetchone()
                return result[0] if result else 0
        except Exception:
            return 0
    
    def _create_initial_schema(self) -> None:
        """Create initial database schema."""
        logger.info("Creating initial database schema")
        
        with self.transaction() as conn:
            cursor = conn.cursor()
            
            # Schema version tracking
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version INTEGER NOT NULL,
                    applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Crew details table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS crew (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    role TEXT,
                    contact TEXT,
                    skills TEXT,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Appliance metadata table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS appliance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Crew availability table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS crew_availability (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    crew_id INTEGER NOT NULL,
                    start_time DATETIME NOT NULL,
                    end_time DATETIME NOT NULL,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (crew_id) REFERENCES crew(id)
                )
            """)
            
            # Appliance availability table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS appliance_availability (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    appliance_id INTEGER NOT NULL,
                    start_time DATETIME NOT NULL,
                    end_time DATETIME NOT NULL,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (appliance_id) REFERENCES appliance(id)
                )
            """)
            
            # Create indexes separately
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_crew_availability_time 
                ON crew_availability (crew_id, start_time, end_time)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_appliance_availability_time 
                ON appliance_availability (appliance_id, start_time, end_time)
            """)
            
            # Record schema version
            cursor.execute("INSERT INTO schema_version (version) VALUES (1)")
            
    def _migrate_schema(self, current_version: int) -> None:
        """Apply schema migrations if needed."""
        if current_version < 1:
            # Future migrations would go here
            pass
    
    def clean_old_availability_data(self, days_to_keep: int = 30) -> int:
        """Clean availability data older than specified days."""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        with self.transaction() as conn:
            cursor = conn.cursor()
            
            # Clean old crew availability
            cursor.execute("""
                DELETE FROM crew_availability 
                WHERE end_time < ?
            """, (cutoff_date,))
            crew_deleted = cursor.rowcount
            
            # Clean old appliance availability  
            cursor.execute("""
                DELETE FROM appliance_availability 
                WHERE end_time < ?
            """, (cutoff_date,))
            appliance_deleted = cursor.rowcount
            
            total_deleted = crew_deleted + appliance_deleted
            if total_deleted > 0:
                logger.info(f"Cleaned {total_deleted} old availability records")
            
            return total_deleted
    
    def get_crew_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get crew member by name."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, name, role, contact, skills 
                FROM crew WHERE name = ?
            """, (name,))
            
            row = cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'name': row[1], 
                    'role': row[2],
                    'contact': row[3],
                    'skills': row[4]
                }
            return None
    
    def upsert_crew_member(self, crew_data: Dict[str, Any]) -> int:
        """Insert or update crew member, returning crew ID."""
        with self.transaction() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO crew (name, role, contact, skills) 
                VALUES (?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    role = excluded.role,
                    contact = excluded.contact,
                    skills = excluded.skills,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                crew_data.get('name'),
                crew_data.get('role'),
                crew_data.get('contact'),
                crew_data.get('skills')
            ))
            
            # Get the crew ID
            cursor.execute("SELECT id FROM crew WHERE name = ?", (crew_data.get('name'),))
            return cursor.fetchone()[0]
    
    def batch_upsert_crew(self, crew_list: List[Dict[str, Any]]) -> None:
        """Batch insert/update crew members."""
        if not crew_list:
            return
            
        with self.transaction() as conn:
            cursor = conn.cursor()
            
            crew_data = [
                (crew.get('name'), crew.get('role'), crew.get('contact'), crew.get('skills'))
                for crew in crew_list
            ]
            
            cursor.executemany("""
                INSERT INTO crew (name, role, contact, skills) 
                VALUES (?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    role = excluded.role,
                    contact = excluded.contact,
                    skills = excluded.skills,
                    updated_at = CURRENT_TIMESTAMP
            """, crew_data)
            
            logger.info(f"Upserted {len(crew_list)} crew members")
    
    def clear_future_availability(self, entity_type: str, entity_id: int, start_time: datetime) -> None:
        """Clear future availability data for an entity."""
        table = f"{entity_type}_availability"
        id_column = f"{entity_type}_id"
        
        with self.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                DELETE FROM {table} 
                WHERE {id_column} = ? AND start_time >= ?
            """, (entity_id, start_time))
            
            if cursor.rowcount > 0:
                logger.debug(f"Cleared {cursor.rowcount} future availability records for {entity_type} {entity_id}")
    
    def batch_insert_availability(self, 
                                entity_type: str, 
                                availability_data: List[tuple]) -> None:
        """Batch insert availability data."""
        if not availability_data:
            return
            
        table = f"{entity_type}_availability"
        id_column = f"{entity_type}_id"
        
        with self.transaction() as conn:
            cursor = conn.cursor()
            cursor.executemany(f"""
                INSERT INTO {table} ({id_column}, start_time, end_time)
                VALUES (?, ?, ?)
            """, availability_data)
            
            logger.debug(f"Inserted {len(availability_data)} {entity_type} availability records")
    
    def get_pool_status(self) -> Dict[str, Any]:
        """Get database connection pool status."""
        with self.db_pool._lock:
            return {
                'total_connections': len(self.db_pool._connections) + len(self.db_pool._in_use),
                'available_connections': len(self.db_pool._connections),
                'in_use_connections': len(self.db_pool._in_use),
                'max_connections': self.db_pool.max_connections,
                'database_path': self.db_path
            }
    
    def get_database_stats(self) -> Dict[str, int]:
        """Get database statistics."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            stats = {}
            for table in ['crew', 'appliance', 'crew_availability', 'appliance_availability']:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                stats[table] = cursor.fetchone()[0]
            
            return stats

# Global database manager instance
_db_manager = None
_db_manager_lock = threading.Lock()

def get_database_manager(db_path: str = "gartan_availability.db") -> DatabaseManager:
    """Get the global database manager instance."""
    global _db_manager
    
    # If requesting a different path or no manager exists, create new one
    if _db_manager is None or _db_manager.db_path != db_path:
        with _db_manager_lock:
            if _db_manager is None or _db_manager.db_path != db_path:
                _db_manager = DatabaseManager(db_path)
                _db_manager.ensure_schema()
    
    return _db_manager
