"""
Refined API layer for Gartan Scraper Bot.

Provides simplified, robust API endpoints with consistent error handling,
performance monitoring, and clean response formatting.
"""

import sqlite3
from typing import Dict, Any, List, Optional, Union, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path
import json

from unified_config import GartanConfig, get_config
from error_handling import (
    ErrorHandler, ErrorInfo, ErrorCategory, ErrorSeverity,
    DatabaseError, ValidationError, handle_exceptions
)
from enhanced_logging import get_logger, log_context, track_performance

@dataclass
class APIResponse:
    """Standardized API response structure."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    timestamp: str = None
    execution_time_ms: Optional[float] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat() + "Z"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = asdict(self)
        # Remove None values to keep response clean
        return {k: v for k, v in result.items() if v is not None}

class APICore:
    """Core API functionality with improved error handling and performance."""
    
    def __init__(self, config: Optional[GartanConfig] = None):
        self.config = config or get_config()
        self.logger = get_logger("gartan.api")
        self.error_handler = ErrorHandler()
        self._db_path = self.config.database.path
        
        # Cache for frequently accessed data
        self._entity_cache: Dict[str, Any] = {}
        self._cache_timeout = timedelta(minutes=5)
        self._last_cache_update: Optional[datetime] = None
    
    def _get_db_connection(self) -> sqlite3.Connection:
        """Get database connection with error handling."""
        try:
            if not Path(self._db_path).exists():
                raise DatabaseError(
                    ErrorInfo(
                        category=ErrorCategory.DATABASE,
                        severity=ErrorSeverity.HIGH,
                        message=f"Database not found: {self._db_path}",
                        details={"db_path": self._db_path}
                    )
                )
            
            conn = sqlite3.connect(self._db_path)
            conn.row_factory = sqlite3.Row
            return conn
            
        except sqlite3.Error as e:
            raise DatabaseError(
                ErrorInfo(
                    category=ErrorCategory.DATABASE,
                    severity=ErrorSeverity.HIGH,
                    message=f"Database connection error: {str(e)}",
                    details={"db_path": self._db_path, "error": str(e)}
                )
            )
    
    def _validate_date_range(self, start_date: Optional[str], end_date: Optional[str]) -> Tuple[datetime, datetime]:
        """Validate and parse date range parameters."""
        try:
            if start_date:
                start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            else:
                start_dt = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
            if end_date:
                end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            else:
                end_dt = start_dt + timedelta(days=1)
            
            if start_dt >= end_dt:
                raise ValidationError(
                    ErrorInfo(
                        category=ErrorCategory.VALIDATION,
                        severity=ErrorSeverity.MEDIUM,
                        message="Start date must be before end date",
                        details={"start_date": start_date, "end_date": end_date}
                    )
                )
            
            # Limit range to prevent excessive queries
            max_range = timedelta(days=30)
            if end_dt - start_dt > max_range:
                raise ValidationError(
                    ErrorInfo(
                        category=ErrorCategory.VALIDATION,
                        severity=ErrorSeverity.MEDIUM,
                        message="Date range too large (max 30 days)",
                        details={"requested_days": (end_dt - start_dt).days}
                    )
                )
            
            return start_dt, end_dt
            
        except ValueError as e:
            raise ValidationError(
                ErrorInfo(
                    category=ErrorCategory.VALIDATION,
                    severity=ErrorSeverity.MEDIUM,
                    message=f"Invalid date format: {str(e)}",
                    details={"start_date": start_date, "end_date": end_date}
                )
            )
    
    def _refresh_entity_cache(self):
        """Refresh the entity cache if needed."""
        now = datetime.now()
        if (self._last_cache_update is None or 
            now - self._last_cache_update > self._cache_timeout):
            
            with track_performance("refresh_entity_cache"):
                conn = self._get_db_connection()
                try:
                    # Cache crew entities
                    crew_cursor = conn.execute("SELECT entity_id, entity_name FROM crew_entities")
                    crew_entities = {row['entity_id']: row['entity_name'] for row in crew_cursor}
                    
                    # Cache appliance entities
                    appliance_cursor = conn.execute("SELECT entity_id, entity_name FROM appliance_entities")
                    appliance_entities = {row['entity_id']: row['entity_name'] for row in appliance_cursor}
                    
                    self._entity_cache = {
                        'crew': crew_entities,
                        'appliances': appliance_entities
                    }
                    self._last_cache_update = now
                    
                finally:
                    conn.close()
    
    @handle_exceptions(error_category=ErrorCategory.EXTERNAL)
    def get_entity_list(self, entity_type: str) -> APIResponse:
        """Get list of entities by type."""
        start_time = datetime.now()
        
        with log_context(operation="get_entity_list", entity_type=entity_type):
            if entity_type not in ["crew", "appliances"]:
                return APIResponse(
                    success=False,
                    error="Invalid entity type. Must be 'crew' or 'appliances'",
                    error_code="INVALID_ENTITY_TYPE"
                )
            
            self._refresh_entity_cache()
            entities = self._entity_cache.get(entity_type, {})
            
            entity_list = [
                {"id": entity_id, "name": name}
                for entity_id, name in entities.items()
            ]
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return APIResponse(
                success=True,
                data=entity_list,
                execution_time_ms=execution_time
            )
    
    @handle_exceptions(error_category=ErrorCategory.EXTERNAL)
    def check_availability(self, entity_type: str, entity_id: str, 
                          start_date: Optional[str] = None, 
                          end_date: Optional[str] = None) -> APIResponse:
        """Check if entity is available in date range."""
        start_time = datetime.now()
        
        with log_context(operation="check_availability", entity_type=entity_type, entity_id=entity_id):
            if entity_type not in ["crew", "appliances"]:
                return APIResponse(
                    success=False,
                    error="Invalid entity type. Must be 'crew' or 'appliances'",
                    error_code="INVALID_ENTITY_TYPE"
                )
            
            # Validate dates
            try:
                start_dt, end_dt = self._validate_date_range(start_date, end_date)
            except (ValidationError, DatabaseError) as e:
                return APIResponse(
                    success=False,
                    error=str(e),
                    error_code=e.error_info.category.value
                )
            
            # Check availability
            table_name = f"{entity_type}_availability"
            conn = self._get_db_connection()
            
            try:
                # Check if entity exists
                entity_cursor = conn.execute(
                    f"SELECT 1 FROM {entity_type}_entities WHERE entity_id = ?",
                    (entity_id,)
                )
                if not entity_cursor.fetchone():
                    return APIResponse(
                        success=False,
                        error=f"Entity not found: {entity_id}",
                        error_code="ENTITY_NOT_FOUND"
                    )
                
                # Check for any availability blocks in the date range
                availability_cursor = conn.execute(f"""
                    SELECT COUNT(*) as available_count
                    FROM {table_name}
                    WHERE entity_id = ?
                    AND start_time < ?
                    AND end_time > ?
                """, (entity_id, end_dt.isoformat(), start_dt.isoformat()))
                
                result = availability_cursor.fetchone()
                is_available = result['available_count'] > 0
                
                execution_time = (datetime.now() - start_time).total_seconds() * 1000
                
                return APIResponse(
                    success=True,
                    data=is_available,
                    execution_time_ms=execution_time
                )
                
            finally:
                conn.close()
    
    @handle_exceptions(error_category=ErrorCategory.EXTERNAL)
    def get_availability_duration(self, entity_type: str, entity_id: str,
                                 start_date: Optional[str] = None,
                                 end_date: Optional[str] = None) -> APIResponse:
        """Get total availability duration for entity in date range."""
        start_time = datetime.now()
        
        with log_context(operation="get_availability_duration", entity_type=entity_type, entity_id=entity_id):
            if entity_type not in ["crew", "appliances"]:
                return APIResponse(
                    success=False,
                    error="Invalid entity type. Must be 'crew' or 'appliances'",
                    error_code="INVALID_ENTITY_TYPE"
                )
            
            # Validate dates
            try:
                start_dt, end_dt = self._validate_date_range(start_date, end_date)
            except (ValidationError, DatabaseError) as e:
                return APIResponse(
                    success=False,
                    error=str(e),
                    error_code=e.error_info.category.value
                )
            
            table_name = f"{entity_type}_availability"
            conn = self._get_db_connection()
            
            try:
                # Check if entity exists
                entity_cursor = conn.execute(
                    f"SELECT 1 FROM {entity_type}_entities WHERE entity_id = ?",
                    (entity_id,)
                )
                if not entity_cursor.fetchone():
                    return APIResponse(
                        success=False,
                        error=f"Entity not found: {entity_id}",
                        error_code="ENTITY_NOT_FOUND"
                    )
                
                # Calculate total duration with proper overlap handling
                duration_cursor = conn.execute(f"""
                    SELECT 
                        start_time,
                        end_time
                    FROM {table_name}
                    WHERE entity_id = ?
                    AND start_time < ?
                    AND end_time > ?
                    ORDER BY start_time
                """, (entity_id, end_dt.isoformat(), start_dt.isoformat()))
                
                blocks = duration_cursor.fetchall()
                
                if not blocks:
                    duration_hours = 0.0
                else:
                    # Calculate total duration with overlap handling
                    total_seconds = 0
                    current_end = None
                    
                    for block in blocks:
                        block_start = max(start_dt, datetime.fromisoformat(block['start_time']))
                        block_end = min(end_dt, datetime.fromisoformat(block['end_time']))
                        
                        if current_end is None or block_start >= current_end:
                            # No overlap
                            total_seconds += (block_end - block_start).total_seconds()
                            current_end = block_end
                        elif block_end > current_end:
                            # Partial overlap
                            total_seconds += (block_end - current_end).total_seconds()
                            current_end = block_end
                    
                    duration_hours = total_seconds / 3600.0
                
                execution_time = (datetime.now() - start_time).total_seconds() * 1000
                
                return APIResponse(
                    success=True,
                    data=f"{duration_hours:.1f}",
                    execution_time_ms=execution_time
                )
                
            finally:
                conn.close()
    
    @handle_exceptions(error_category=ErrorCategory.EXTERNAL)
    def get_availability_blocks(self, entity_type: str, entity_id: str,
                               start_date: Optional[str] = None,
                               end_date: Optional[str] = None) -> APIResponse:
        """Get detailed availability blocks for entity."""
        start_time = datetime.now()
        
        with log_context(operation="get_availability_blocks", entity_type=entity_type, entity_id=entity_id):
            if entity_type not in ["crew", "appliances"]:
                return APIResponse(
                    success=False,
                    error="Invalid entity type. Must be 'crew' or 'appliances'",
                    error_code="INVALID_ENTITY_TYPE"
                )
            
            # Validate dates
            try:
                start_dt, end_dt = self._validate_date_range(start_date, end_date)
            except (ValidationError, DatabaseError) as e:
                return APIResponse(
                    success=False,
                    error=str(e),
                    error_code=e.error_info.category.value
                )
            
            table_name = f"{entity_type}_availability"
            conn = self._get_db_connection()
            
            try:
                # Check if entity exists
                entity_cursor = conn.execute(
                    f"SELECT entity_name FROM {entity_type}_entities WHERE entity_id = ?",
                    (entity_id,)
                )
                entity_row = entity_cursor.fetchone()
                if not entity_row:
                    return APIResponse(
                        success=False,
                        error=f"Entity not found: {entity_id}",
                        error_code="ENTITY_NOT_FOUND"
                    )
                
                # Get availability blocks
                blocks_cursor = conn.execute(f"""
                    SELECT 
                        start_time,
                        end_time,
                        created_at
                    FROM {table_name}
                    WHERE entity_id = ?
                    AND start_time < ?
                    AND end_time > ?
                    ORDER BY start_time
                """, (entity_id, end_dt.isoformat(), start_dt.isoformat()))
                
                blocks = []
                for row in blocks_cursor:
                    block_start = max(start_dt, datetime.fromisoformat(row['start_time']))
                    block_end = min(end_dt, datetime.fromisoformat(row['end_time']))
                    duration_hours = (block_end - block_start).total_seconds() / 3600.0
                    
                    blocks.append({
                        "start_time": block_start.isoformat() + "Z",
                        "end_time": block_end.isoformat() + "Z",
                        "duration_hours": round(duration_hours, 2)
                    })
                
                execution_time = (datetime.now() - start_time).total_seconds() * 1000
                
                return APIResponse(
                    success=True,
                    data={
                        "entity_id": entity_id,
                        "entity_name": entity_row['entity_name'],
                        "entity_type": entity_type,
                        "query_start": start_dt.isoformat() + "Z",
                        "query_end": end_dt.isoformat() + "Z",
                        "blocks": blocks,
                        "total_blocks": len(blocks)
                    },
                    execution_time_ms=execution_time
                )
                
            finally:
                conn.close()
    
    @handle_exceptions(error_category=ErrorCategory.EXTERNAL)
    def get_system_status(self) -> APIResponse:
        """Get system status and health information."""
        start_time = datetime.now()
        
        with log_context(operation="get_system_status"):
            conn = self._get_db_connection()
            
            try:
                # Get database statistics
                crew_count_cursor = conn.execute("SELECT COUNT(*) as count FROM crew_entities")
                crew_count = crew_count_cursor.fetchone()['count']
                
                appliance_count_cursor = conn.execute("SELECT COUNT(*) as count FROM appliance_entities")
                appliance_count = appliance_count_cursor.fetchone()['count']
                
                # Get latest data timestamp
                latest_cursor = conn.execute("""
                    SELECT MAX(created_at) as latest_update
                    FROM (
                        SELECT created_at FROM crew_availability
                        UNION
                        SELECT created_at FROM appliance_availability
                    )
                """)
                latest_row = latest_cursor.fetchone()
                latest_update = latest_row['latest_update'] if latest_row['latest_update'] else None
                
                # Check database file size
                db_size_mb = Path(self._db_path).stat().st_size / 1024 / 1024 if Path(self._db_path).exists() else 0
                
                execution_time = (datetime.now() - start_time).total_seconds() * 1000
                
                return APIResponse(
                    success=True,
                    data={
                        "database_status": "healthy",
                        "crew_entities": crew_count,
                        "appliance_entities": appliance_count,
                        "latest_data_update": latest_update,
                        "database_size_mb": round(db_size_mb, 2),
                        "api_version": "2.0"
                    },
                    execution_time_ms=execution_time
                )
                
            finally:
                conn.close()

# Global API core instance
_api_core: Optional[APICore] = None

def get_api_core() -> APICore:
    """Get the global API core instance."""
    global _api_core
    if _api_core is None:
        _api_core = APICore()
    return _api_core

# Convenience functions for direct API access
def get_crew_list() -> APIResponse:
    """Get list of crew entities."""
    return get_api_core().get_entity_list("crew")

def get_appliance_list() -> APIResponse:
    """Get list of appliance entities."""
    return get_api_core().get_entity_list("appliances")

def is_crew_available(crew_id: str, start_date: Optional[str] = None, 
                     end_date: Optional[str] = None) -> APIResponse:
    """Check if crew member is available."""
    return get_api_core().check_availability("crew", crew_id, start_date, end_date)

def is_appliance_available(appliance_id: str, start_date: Optional[str] = None,
                          end_date: Optional[str] = None) -> APIResponse:
    """Check if appliance is available."""
    return get_api_core().check_availability("appliances", appliance_id, start_date, end_date)

def get_crew_duration(crew_id: str, start_date: Optional[str] = None,
                     end_date: Optional[str] = None) -> APIResponse:
    """Get crew availability duration."""
    return get_api_core().get_availability_duration("crew", crew_id, start_date, end_date)

def get_appliance_duration(appliance_id: str, start_date: Optional[str] = None,
                          end_date: Optional[str] = None) -> APIResponse:
    """Get appliance availability duration."""
    return get_api_core().get_availability_duration("appliances", appliance_id, start_date, end_date)
