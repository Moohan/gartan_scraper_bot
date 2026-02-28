"""Database storage functions for Gartan Scraper Bot."""

import sqlite3
from datetime import datetime, timedelta
from typing import Any, Dict, List

from config import config

# Configure sqlite3 datetime adapters for Python 3.12+ compatibility
sqlite3.register_adapter(datetime, lambda dt: dt.isoformat())
sqlite3.register_converter(
    "datetime", lambda dt: datetime.fromisoformat(dt.decode("utf-8"))
)

CREW_DETAILS_TABLE = """
CREATE TABLE IF NOT EXISTS crew (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    role TEXT,
    skills TEXT,
    contract_hours TEXT
);
"""

APPLIANCE_META_TABLE = """
CREATE TABLE IF NOT EXISTS appliance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);
"""
sqlite3.register_converter("DATETIME", lambda b: datetime.fromisoformat(b.decode()))

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
    conn = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
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
    # ⚡ Performance: Add a composite index on (crew_id, start_time, end_time).
    # This is the most effective indexing strategy for the common API query
    # pattern, which filters by crew member and a specific time range.
    c.execute(
        "CREATE INDEX IF NOT EXISTS idx_crew_availability_crew_times ON crew_availability(crew_id, start_time, end_time)"
    )
    conn.commit()
    return conn


def _convert_slots_to_blocks(
    availability: Dict[str, bool],
) -> List[Dict[str, datetime]]:
    """Converts a dictionary of slots into a list of continuous availability blocks.

    Dynamically detects the resolution (e.g. 15m or 60m) and correctly handles
    time gaps between blocks.
    """
    from logging_config import get_logger

    logger = get_logger()

    if not availability:
        return []

    # Sort availability by timestamp
    sorted_slots = sorted(
        [
            (datetime.strptime(slot, "%d/%m/%Y %H%M"), is_available)
            for slot, is_available in availability.items()
        ]
    )

    # 1. Determine Resolution (default to 60m if not detectable, as seen in Gartan)
    resolution = timedelta(minutes=60)
    if len(sorted_slots) > 1:
        # Find the most common difference between adjacent slots
        diffs = []
        for i in range(len(sorted_slots) - 1):
            diff = sorted_slots[i + 1][0] - sorted_slots[i][0]
            if diff > timedelta(0):
                diffs.append(diff)

        if diffs:
            # Simple heuristic: use the minimum positive difference as the resolution
            resolution = min(diffs)
            logger.debug(f"Detected slot resolution: {resolution}")

    blocks = []
    in_block = False
    block_start = None
    prev_slot_time = None

    for i, (slot_time, is_available) in enumerate(sorted_slots):
        if is_available:
            if not in_block:
                # Start new block
                in_block = True
                block_start = slot_time
            else:
                # Already in a block, check for gaps
                if prev_slot_time and (slot_time - prev_slot_time) > resolution:
                    # Gap detected! Close previous block and start new one
                    blocks.append(
                        {
                            "start_time": block_start,
                            "end_time": prev_slot_time + resolution,
                        }
                    )
                    block_start = slot_time
        else:
            if in_block:
                # Available -> Unavailable transition. Close block at the current unavailable slot.
                blocks.append({"start_time": block_start, "end_time": slot_time})
                in_block = False
                block_start = None

        prev_slot_time = slot_time

    # Close the last block if still open
    if in_block and block_start and prev_slot_time:
        blocks.append(
            {"start_time": block_start, "end_time": prev_slot_time + resolution}
        )

    logger.debug(
        f"Converted {len(availability)} slots into {len(blocks)} blocks using {resolution} resolution."
    )
    return blocks


def insert_crew_details(crew_list: list, db_conn=None):
    """
    Insert or update crew details (name, role, contract_hours, skills) into crew table.
    Uses optimized batch operations and connection pooling.

    crew_list: list of dicts with 'name', 'role', 'contract_hours', and 'skills' keys
    db_conn: an existing database connection to use (connection object, not path)
    """
    if db_conn is not None:
        conn = db_conn
        should_close = False
    else:
        conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
        should_close = True

    try:
        c = conn.cursor()

        # Prepare batch data for efficient bulk insert
        crew_data = []
        for crew in crew_list:
            name = crew.get("name")
            role = crew.get("role")
            contract_hours = crew.get("contract_hours")
            skills = crew.get("skills")
            crew_data.append((name, role, skills, contract_hours))

        # Use executemany for batch operations
        c.executemany(
            """
            INSERT INTO crew (name, role, skills, contract_hours) VALUES (?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET role=excluded.role, skills=excluded.skills, contract_hours=excluded.contract_hours
            """,
            crew_data,
        )
        conn.commit()

    finally:
        if should_close:
            conn.close()


def insert_crew_availability(crew_list: List[Dict[str, Any]], db_conn=None):
    """
    Converts crew availability slots into blocks and inserts them into the database.
    Cleans up overlapping blocks for the date range being processed.
    Uses optimized batch operations and connection pooling.
    """
    if db_conn is not None:
        conn = db_conn
        should_close = False
    else:
        conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
        should_close = True

    try:
        c = conn.cursor()
        from logging_config import get_logger

        logger = get_logger()
        logger.debug(f"Inserting crew availability for {len(crew_list)} crew members.")

        # Determine the date range being processed
        all_dates = set()
        min_date = None
        max_date = None

        for crew in crew_list:
            for slot_time in crew.get("availability", {}):
                date_str = slot_time.split()[0]  # Extract date part
                date_obj = datetime.strptime(date_str, "%d/%m/%Y").date()
                all_dates.add(date_obj)

        if all_dates:
            min_date = min(all_dates)
            max_date = max(all_dates)
            logger.debug(f"Processing date range: {min_date} to {max_date}")

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

            # Clean up existing blocks that overlap with the date range being processed
            if min_date and max_date:
                # We use a half-open interval [start, end) for the processed range.
                # A block is deleted if it has ANY overlap with this range.
                # Logic: start_time < range_end AND end_time > range_start
                range_start = datetime.combine(min_date, datetime.min.time())
                range_end = datetime.combine(
                    max_date + timedelta(days=1), datetime.min.time()
                )

                c.execute(
                    """
                    DELETE FROM crew_availability
                    WHERE crew_id = ?
                    AND start_time < ?
                    AND end_time > ?
                """,
                    (crew_id, range_end, range_start),
                )

                deleted_count = c.rowcount
                if deleted_count > 0:
                    logger.debug(
                        f"Deleted {deleted_count} existing blocks for {name} overlapping {min_date} to {max_date}"
                    )

            availability_blocks = _convert_slots_to_blocks(crew["availability"])
            logger.debug(
                f"Found {len(availability_blocks)} availability blocks for {name}."
            )

            # Prepare batch data for new blocks
            for block in availability_blocks:
                logger.debug(
                    f"Inserting block for {name}: {block['start_time']} -> {block['end_time']}"
                )
                crew_availability_data.append(
                    (crew_id, block["start_time"], block["end_time"])
                )

        # Batch insert all new availability blocks
        if crew_availability_data:
            c.executemany(
                """
                INSERT OR REPLACE INTO crew_availability (crew_id, start_time, end_time)
                VALUES (?, ?, ?)
                """,
                crew_availability_data,
            )
            logger.debug(
                f"[ok] Saved crew availability for {len(crew_list)} crew members to {DB_PATH}"
            )

        conn.commit()
        defrag_availability(db_conn=conn)

    finally:
        if should_close:
            conn.close()


def insert_appliance_availability(appliance_obj: Dict[str, Any], db_conn=None):
    """Convert appliance slot availability into blocks and insert non-duplicates."""
    from logging_config import get_logger

    logger = get_logger()
    if db_conn is not None:
        conn = db_conn
        should_close = False
    else:
        conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
        should_close = True
    c = conn.cursor()

    # Identify the date range for cleanup based on keys in the data
    all_dates = set()
    for info in appliance_obj.values():
        for slot in info.get("availability", {}).keys():
            try:
                date_str = slot.split(" ")[0]
                date_obj = datetime.strptime(date_str, "%d/%m/%Y").date()
                all_dates.add(date_obj)
            except (ValueError, IndexError):
                logger.debug(f"Failed to parse date from slot: {slot}")
                continue

    min_date = min(all_dates) if all_dates else None
    max_date = max(all_dates) if all_dates else None

    try:
        for appliance, info in appliance_obj.items():
            c.execute("INSERT OR IGNORE INTO appliance (name) VALUES (?)", (appliance,))
            c.execute("SELECT id FROM appliance WHERE name=?", (appliance,))
            row = c.fetchone()
            if not row:
                continue
            appliance_id = row[0]

            # Clean up existing blocks that overlap with the date range being processed
            if min_date and max_date:
                range_start = datetime.combine(min_date, datetime.min.time())
                range_end = datetime.combine(
                    max_date + timedelta(days=1), datetime.min.time()
                )

                c.execute(
                    """
                    DELETE FROM appliance_availability
                    WHERE appliance_id = ?
                    AND start_time < ?
                    AND end_time > ?
                """,
                    (appliance_id, range_end, range_start),
                )

            availability_blocks = _convert_slots_to_blocks(info["availability"])
            for block in availability_blocks:
                c.execute(
                    """
                    INSERT OR REPLACE INTO appliance_availability (appliance_id, start_time, end_time)
                    VALUES (?, ?, ?)
                    """,
                    (appliance_id, block["start_time"], block["end_time"]),
                )
        conn.commit()
        defrag_availability(db_conn=conn)
    finally:
        if should_close:
            conn.close()


def defrag_availability(db_conn=None):
    """Merge touching or overlapping availability blocks in the database.

    This joins blocks like [08:00, 10:00] and [10:00, 12:00] into [08:00, 12:00].
    """
    from logging_config import get_logger

    logger = get_logger()

    if db_conn is not None:
        conn = db_conn
        should_close = False
    else:
        conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
        should_close = True
    c = conn.cursor()

    try:
        for table in ["crew_availability", "appliance_availability"]:
            id_col = "crew_id" if table == "crew_availability" else "appliance_id"

            # Simple iterative merging logic:
            # 1. Select all blocks sorted by id and start_time
            c.execute(
                f"SELECT id, {id_col}, start_time, end_time FROM {table} ORDER BY {id_col}, start_time"  # nosec B608
            )
            rows = c.fetchall()

            if not rows:
                continue

            merged_count = 0
            prev_id, _, prev_end, prev_row_id = (
                rows[0][1],
                rows[0][2],
                rows[0][3],
                rows[0][0],
            )

            for i in range(1, len(rows)):
                curr_row_id, curr_id, curr_start, curr_end = rows[i]

                # Check for touch or overlap
                if curr_id == prev_id and curr_start <= prev_end:
                    # Overlap! Merge curr into prev
                    new_end = max(prev_end, curr_end)
                    if new_end != prev_end:
                        # Update prev block
                        c.execute(
                            f"UPDATE {table} SET end_time = ? WHERE id = ?",  # nosec B608
                            (new_end, prev_row_id),
                        )
                        prev_end = new_end

                    # Delete current block
                    c.execute(
                        f"DELETE FROM {table} WHERE id = ?", (curr_row_id,)
                    )  # nosec B608
                    merged_count += 1
                else:
                    # Move to next block
                    prev_id, _, prev_end, prev_row_id = (
                        curr_id,
                        curr_start,
                        curr_end,
                        curr_row_id,
                    )

            if merged_count > 0:
                logger.info(f"Merged {merged_count} blocks in {table}")

        conn.commit()
    finally:
        if should_close:
            conn.close()
