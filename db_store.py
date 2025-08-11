CREW_DETAILS_TABLE = """
CREATE TABLE IF NOT EXISTS crew (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    role TEXT,
    contact TEXT,
    skills TEXT
);
"""

APPLIANCE_META_TABLE = """
CREATE TABLE IF NOT EXISTS appliance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);
"""
import sqlite3
from datetime import datetime, timedelta
from typing import Any, Dict, List

from config import config

DB_PATH = config.db_path

CREW_TABLE = """
CREATE TABLE IF NOT EXISTS crew_availability (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    crew_id INTEGER NOT NULL,
    start_time DATETIME NOT NULL,
    end_time DATETIME NOT NULL,
    FOREIGN KEY (crew_id) REFERENCES crew(id)
);
"""

APPLIANCE_TABLE = """
CREATE TABLE IF NOT EXISTS appliance_availability (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    appliance_id INTEGER NOT NULL,
    start_time DATETIME NOT NULL,
    end_time DATETIME NOT NULL,
    FOREIGN KEY (appliance_id) REFERENCES appliance(id)
);
"""


def init_db(db_path: str = DB_PATH, reset: bool = False):
    """Initialise the database schema.

    If reset=True the existing tables are dropped (legacy behaviour).
    Otherwise tables are created if they do not already exist and existing
    data is preserved to allow historical accumulation across scraper runs.
    """
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    if reset:
        c.execute("DROP TABLE IF EXISTS crew_availability")
        c.execute("DROP TABLE IF EXISTS appliance_availability")
        c.execute("DROP TABLE IF EXISTS crew")
        c.execute("DROP TABLE IF EXISTS appliance")
    # (Re)create tables if missing
    c.execute(CREW_DETAILS_TABLE)
    c.execute(APPLIANCE_META_TABLE)
    c.execute(CREW_TABLE)
    c.execute(APPLIANCE_TABLE)
    # Idempotent indexes to prevent duplicate block inserts
    c.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_crew_block ON crew_availability(crew_id,start_time,end_time)"
    )
    c.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_appliance_block ON appliance_availability(appliance_id,start_time,end_time)"
    )
    conn.commit()
    return conn


def _convert_slots_to_blocks(
    availability: Dict[str, bool],
) -> List[Dict[str, datetime]]:
    """Converts a dictionary of 15-minute slots into a list of continuous availability blocks."""
    from logging_config import get_logger

    logger = get_logger()

    if not availability:
        logger.debug("Availability data is empty, returning no blocks.")
        return []

    # Convert slot strings to datetime objects and sort them
    sorted_slots = sorted(
        [
            (datetime.strptime(slot, "%d/%m/%Y %H%M"), is_available)
            for slot, is_available in availability.items()
        ]
    )
    logger.debug(f"Processing {len(sorted_slots)} sorted slots.")

    blocks = []
    in_block = False
    block_start = None

    for i, (slot_time, is_available) in enumerate(sorted_slots):
        if is_available and not in_block:
            in_block = True
            block_start = slot_time
            logger.debug(
                f"Started a new block at {block_start.strftime('%Y-%m-%d %H:%M')}"
            )
        elif not is_available and in_block:
            in_block = False
            # The block ends at the start of the first unavailable slot
            block_end = slot_time
            if block_start:
                blocks.append({"start_time": block_start, "end_time": block_end})
                logger.debug(
                    f"Closed block: {block_start.strftime('%Y-%m-%d %H:%M')} to {block_end.strftime('%Y-%m-%d %H:%M')}"
                )
            block_start = None

    # If the session ends while in an availability block, close it.
    if in_block and block_start:
        # The last block extends 15 minutes past the last slot's start time
        last_slot_time = sorted_slots[-1][0]
        block_end = last_slot_time + timedelta(minutes=15)
        blocks.append({"start_time": block_start, "end_time": block_end})
        logger.debug(
            f"Closed final block: {block_start.strftime('%Y-%m-%d %H:%M')} to {block_end.strftime('%Y-%m-%d %H:%M')}"
        )

    logger.debug(f"Converted {len(availability)} slots into {len(blocks)} blocks.")
    return blocks


def insert_crew_details(
    crew_list: list, contact_map: dict = None, db_conn: sqlite3.Connection = None
):
    """
    Insert or update crew details (name, role, contact) into crew table.
    Uses optimized batch operations and connection pooling.

    crew_list: list of dicts with 'name' and 'role' keys
    contact_map: dict mapping name to contact info
    db_conn: an existing database connection to use (connection object, not path)
    """
    if db_conn is not None:
        conn = db_conn
        should_close = False
    else:
        conn = sqlite3.connect(DB_PATH)
        should_close = True

    try:
        c = conn.cursor()

        # Prepare batch data for efficient bulk insert
        crew_data = []
        for crew in crew_list:
            name = crew.get("name")
            role = crew.get("role")
            skills = crew.get("skills")
            contact = None
            if contact_map and name in contact_map:
                contact = contact_map[name]
            crew_data.append((name, role, contact, skills))

        # Use executemany for batch operations
        c.executemany(
            """
            INSERT INTO crew (name, role, contact, skills) VALUES (?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET role=excluded.role, contact=excluded.contact, skills=excluded.skills
            """,
            crew_data
        )
        conn.commit()

    finally:
        if should_close:
            conn.close()


def insert_crew_availability(
    crew_list: List[Dict[str, Any]], db_conn: sqlite3.Connection = None
):
    """
    Converts crew availability slots into blocks and inserts them into the database.
    Uses optimized batch operations and connection pooling.
    """
    if db_conn is not None:
        conn = db_conn
        should_close = False
    else:
        conn = sqlite3.connect(DB_PATH)
        should_close = True

    try:
        c = conn.cursor()
        from logging_config import get_logger
        logger = get_logger()
        logger.debug(f"Inserting crew availability for {len(crew_list)} crew members.")

        # Batch data preparation
        crew_availability_data = []

        for crew in crew_list:
            name = crew["name"]
            logger.debug(f"Processing crew member: {name}")
            c.execute("SELECT id FROM crew WHERE name=?", (name,))
            row = c.fetchone()
            if not row:
                logger.warning(f"Could not find crew_id for {name}, skipping.")
                continue
            crew_id = row[0]

            availability_blocks = _convert_slots_to_blocks(crew["availability"])
            logger.debug(
                f"Found {len(availability_blocks)} availability blocks for {name}."
            )

            # Prepare batch data instead of individual inserts
            for block in availability_blocks:
                logger.debug(
                    f"Inserting block for {name}: {block['start_time']} -> {block['end_time']}"
                )
                crew_availability_data.append((
                    crew_id,
                    block["start_time"],
                    block["end_time"]
                ))

        # Batch insert all availability blocks
        if crew_availability_data:
            c.executemany(
                """
                INSERT OR IGNORE INTO crew_availability (crew_id, start_time, end_time)
                VALUES (?, ?, ?)
                """,
                crew_availability_data,
            )
            logger.debug(f"[ok] Saved crew availability for {len(crew_list)} crew members to {DB_PATH}")

        conn.commit()

    finally:
        if should_close:
            conn.close()


def insert_appliance_availability(
    appliance_obj: Dict[str, Any], db_conn: sqlite3.Connection = None
):
    """Convert appliance slot availability into blocks and insert non-duplicates."""
    if db_conn is not None:
        conn = db_conn
        should_close = False
    else:
        conn = sqlite3.connect(DB_PATH)
        should_close = True
    c = conn.cursor()
    try:
        for appliance, info in appliance_obj.items():
            c.execute("INSERT OR IGNORE INTO appliance (name) VALUES (?)", (appliance,))
            c.execute("SELECT id FROM appliance WHERE name=?", (appliance,))
            row = c.fetchone()
            if not row:
                continue
            appliance_id = row[0]
            availability_blocks = _convert_slots_to_blocks(info["availability"])
            for block in availability_blocks:
                c.execute(
                    """
                    INSERT OR IGNORE INTO appliance_availability (appliance_id, start_time, end_time)
                    VALUES (?, ?, ?)
                    """,
                    (appliance_id, block["start_time"], block["end_time"]),
                )
        conn.commit()
    finally:
        if should_close:
            conn.close()
