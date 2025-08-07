"""
Improved Database Storage Module

This module provides high-level database operations using the new DatabaseManager.
It maintains backward compatibility while improving efficiency and robustness.
"""

import sqlite3
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging
import threading
from database_manager import get_database_manager

logger = logging.getLogger(__name__)

# Legacy compatibility - maintain existing interface
DB_PATH = "gartan_availability.db"

def init_db(db_path: str = DB_PATH) -> sqlite3.Connection:
    """
    Initialize database with improved schema management.
    
    Note: This function maintains backward compatibility but now uses
    the new DatabaseManager for improved reliability.
    """
    db_manager = get_database_manager(db_path)
    db_manager.ensure_schema()
    
    # Return a connection for backward compatibility
    # In new code, prefer using DatabaseManager directly
    return db_manager.get_connection().__enter__()

def _convert_slots_to_blocks(availability: Dict[str, bool]) -> List[Dict[str, datetime]]:
    """
    Converts a dictionary of 15-minute slots into a list of continuous availability blocks.
    
    This function is optimized for better performance and clarity.
    """
    if not availability:
        return []
    
    # Sort slots by time for sequential processing
    sorted_slots = sorted(availability.items())
    blocks = []
    current_block = None
    
    for slot_time_str, is_available in sorted_slots:
        if not is_available:
            # End current block if we hit unavailable time
            if current_block:
                blocks.append(current_block)
                current_block = None
            continue
        
        try:
            # Parse time string (format: "DD/MM/YYYY HHMM")
            slot_time = datetime.strptime(slot_time_str, "%d/%m/%Y %H%M")
        except ValueError:
            logger.warning(f"Invalid time format: {slot_time_str}")
            continue
        
        if current_block is None:
            # Start new block
            current_block = {
                "start_time": slot_time,
                "end_time": slot_time + timedelta(minutes=15)
            }
        else:
            # Check if this slot continues the current block
            expected_time = current_block["end_time"]
            if slot_time == expected_time:
                # Extend current block
                current_block["end_time"] = slot_time + timedelta(minutes=15)
            else:
                # Gap found, finish current block and start new one
                blocks.append(current_block)
                current_block = {
                    "start_time": slot_time,
                    "end_time": slot_time + timedelta(minutes=15)
                }
    
    # Don't forget the last block
    if current_block:
        blocks.append(current_block)
    
    return blocks

def insert_crew_details(crew_list: List[Dict[str, Any]], 
                       contact_map: Optional[Dict[str, str]] = None, 
                       db_conn: Optional[sqlite3.Connection] = None) -> None:
    """
    Insert or update crew details using improved database management.
    
    Args:
        crew_list: List of crew dictionaries with name, role, skills
        contact_map: Optional mapping of crew names to contact info
        db_conn: Legacy connection parameter (ignored in new implementation)
    """
    if not crew_list:
        logger.info("No crew data to insert")
        return
    
    db_manager = get_database_manager()
    contact_map = contact_map or {}
    
    # Prepare crew data with contact information
    enriched_crew_list = []
    for crew in crew_list:
        crew_data = {
            'name': crew.get('name'),
            'role': crew.get('role'),
            'skills': crew.get('skills'),
            'contact': contact_map.get(crew.get('name'))
        }
        enriched_crew_list.append(crew_data)
    
    # Use batch operation for efficiency
    db_manager.batch_upsert_crew(enriched_crew_list)
    logger.info(f"Successfully processed {len(crew_list)} crew members")

def insert_crew_availability(crew_list: List[Dict[str, Any]], 
                           db_conn: Optional[sqlite3.Connection] = None) -> None:
    """
    Insert crew availability data using improved batch operations.
    
    Args:
        crew_list: List of crew dictionaries with availability data
        db_conn: Legacy connection parameter (ignored in new implementation)
    """
    if not crew_list:
        logger.info("No crew availability data to insert")
        return
    
    db_manager = get_database_manager()
    availability_data = []
    
    for crew in crew_list:
        name = crew.get('name')
        if not name:
            logger.warning("Crew member missing name, skipping")
            continue
        
        # Get crew ID
        crew_info = db_manager.get_crew_by_name(name)
        if not crew_info:
            logger.warning(f"Crew member {name} not found in database, skipping availability")
            continue
        
        crew_id = crew_info['id']
        availability = crew.get('availability', {})
        
        if not availability:
            logger.debug(f"No availability data for {name}")
            continue
        
        # Convert slots to blocks
        blocks = _convert_slots_to_blocks(availability)
        logger.debug(f"Converted {len(availability)} slots to {len(blocks)} blocks for {name}")
        
        # Prepare batch data
        for block in blocks:
            availability_data.append((
                crew_id,
                block['start_time'],
                block['end_time']
            ))
    
    if availability_data:
        # Clear existing future availability to avoid duplicates
        now = datetime.now()
        for crew in crew_list:
            crew_info = db_manager.get_crew_by_name(crew.get('name'))
            if crew_info:
                db_manager.clear_future_availability('crew', crew_info['id'], now)
        
        # Batch insert new availability
        db_manager.batch_insert_availability('crew', availability_data)
        logger.info(f"Inserted {len(availability_data)} crew availability blocks")
    else:
        logger.info("No availability blocks to insert")

def insert_appliance_availability(appliance_obj: Dict[str, Any], 
                                db_conn: Optional[sqlite3.Connection] = None) -> None:
    """
    Insert appliance availability data using improved database management.
    
    Args:
        appliance_obj: Dictionary mapping appliance names to availability data
        db_conn: Legacy connection parameter (ignored in new implementation)
    """
    if not appliance_obj:
        logger.info("No appliance availability data to insert")
        return
    
    db_manager = get_database_manager()
    availability_data = []
    
    for appliance_name, info in appliance_obj.items():
        # Ensure appliance exists
        with db_manager.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO appliance (name) VALUES (?)", (appliance_name,))
            cursor.execute("SELECT id FROM appliance WHERE name = ?", (appliance_name,))
            
            row = cursor.fetchone()
            if not row:
                logger.warning(f"Failed to get/create appliance {appliance_name}")
                continue
            
            appliance_id = row[0]
        
        availability = info.get('availability', {})
        if not availability:
            logger.debug(f"No availability data for appliance {appliance_name}")
            continue
        
        # Convert slots to blocks
        blocks = _convert_slots_to_blocks(availability)
        logger.debug(f"Converted {len(availability)} slots to {len(blocks)} blocks for {appliance_name}")
        
        # Clear existing future availability
        now = datetime.now()
        db_manager.clear_future_availability('appliance', appliance_id, now)
        
        # Prepare batch data
        for block in blocks:
            availability_data.append((
                appliance_id,
                block['start_time'],
                block['end_time']
            ))
    
    if availability_data:
        # Batch insert new availability
        db_manager.batch_insert_availability('appliance', availability_data)
        logger.info(f"Inserted {len(availability_data)} appliance availability blocks")
    else:
        logger.info("No appliance availability blocks to insert")

def get_database_health() -> Dict[str, Any]:
    """
    Get database health information.
    
    Returns:
        Dictionary with database statistics and health indicators
    """
    db_manager = get_database_manager()
    stats = db_manager.get_database_stats()
    
    # Add health indicators
    health = {
        'stats': stats,
        'healthy': stats.get('crew', 0) > 0,
        'has_recent_data': False
    }
    
    # Check for recent availability data
    with db_manager.get_connection() as conn:
        cursor = conn.cursor()
        cutoff = datetime.now() - timedelta(hours=24)
        
        cursor.execute("""
            SELECT COUNT(*) FROM crew_availability 
            WHERE end_time > ?
        """, (cutoff,))
        
        recent_crew_blocks = cursor.fetchone()[0]
        health['has_recent_data'] = recent_crew_blocks > 0
        health['recent_crew_blocks'] = recent_crew_blocks
    
    return health

def cleanup_old_data(days_to_keep: int = 30) -> int:
    """
    Clean up old availability data.
    
    Args:
        days_to_keep: Number of days of data to retain
        
    Returns:
        Number of records deleted
    """
    db_manager = get_database_manager()
    return db_manager.clean_old_availability_data(days_to_keep)

# Legacy compatibility exports
__all__ = [
    'init_db',
    'insert_crew_details', 
    'insert_crew_availability',
    'insert_appliance_availability',
    'get_database_health',
    'cleanup_old_data'
]
