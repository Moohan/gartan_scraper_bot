import logging
from datetime import datetime as dt

from utils import log_debug


def _calculate_availability_summary(
    slot_tuples: list[tuple[dt, bool]], now: dt
) -> dict:
    """
    Calculates availability summary fields from a sorted list of (datetime, available) tuples.
    """
    next_avail = None
    next_avail_until = None
    available_now = False
    available_for = None

    # Check if available right now
    covering_idx = None
    for idx, (slot_dt, _) in enumerate(slot_tuples):
        if slot_dt > now:
            covering_idx = idx - 1 if idx > 0 else 0
            break
    if covering_idx is None and slot_tuples:
        covering_idx = len(slot_tuples) - 1

    if covering_idx is not None:
        _, avail = slot_tuples[covering_idx]
        if avail:
            available_now = True

    # Find the next continuous block of availability
    for idx, (slot_dt, avail) in enumerate(slot_tuples):
        if slot_dt >= now and avail:
            next_avail = slot_dt.strftime("%d/%m/%Y %H:%M")
            last_true_dt = slot_dt
            next_avail_until_dt = None

            for j in range(idx + 1, len(slot_tuples)):
                next_dt, next_avail_val = slot_tuples[j]
                if next_avail_val:
                    last_true_dt = next_dt
                    if (last_true_dt - slot_dt).total_seconds() / 3600.0 >= 72:
                        break  # Stop if we have a 72h+ block
                else:
                    next_avail_until_dt = next_dt
                    break

            # Calculate available_for based on the block found
            duration_hours = (last_true_dt - slot_dt).total_seconds() / 3600.0
            if duration_hours >= 72:
                available_for = ">72h"
            else:
                # Add the duration of the last slot (15 mins)
                duration_hours += 0.25
                available_for = f"{round(duration_hours, 2)}h"

            if next_avail_until_dt:
                next_avail_until = next_avail_until_dt.strftime("%d/%m/%Y %H:%M")

            break  # Found the first available block, so we are done

    return {
        "available_now": available_now,
        "next_available": next_avail,
        "next_available_until": next_avail_until,
        "available_for": available_for,
    }


def aggregate_appliance_availability(daily_appliance_lists, crew_list_agg=None):
    """
    Aggregate appliance availability across multiple days, calculate next_available, next_available_until, available_now, available_for.
    Also add a 'crew' entry: list of crew available during the next available period for the appliance.
    Args:
        daily_appliance_lists: list of dicts (from parse_appliance_availability)
        crew_list_agg: list of crew dicts (from aggregate_crew_availability)
    Returns:
        list of dicts, one per appliance, with merged slot data and summary fields
    """
    from datetime import datetime as dt

    appliance_dict = {}
    # Merge all slot availabilities for each appliance
    for daily in daily_appliance_lists:
        for appliance, data in daily.items():
            if appliance not in appliance_dict:
                appliance_dict[appliance] = {"appliance": appliance, "availability": {}}
            appliance_dict[appliance]["availability"].update(
                data.get("availability", {})
            )
    # Now recalculate summary fields for each appliance
    now = dt.now()
    for appliance, entry in appliance_dict.items():
        availability = entry["availability"]
        slot_tuples = []
        for slot, avail in availability.items():
            try:
                slot_dt = dt.strptime(slot, "%d/%m/%Y %H%M")
                slot_tuples.append((slot_dt, avail))
            except Exception:
                continue
        slot_tuples.sort()

        summary = _calculate_availability_summary(slot_tuples, now)
        entry.update(summary)

        # Add crew available during the next available period
        entry["crew"] = []
        if crew_list_agg and entry["next_available"]:
            next_avail_dt = dt.strptime(entry["next_available"], "%d/%m/%Y %H:%M")

            for crew in crew_list_agg:
                crew_avail = crew.get("availability", {})
                # Check if crew is available at the start of the appliance's next available period
                slot_key_to_check = next_avail_dt.strftime("%d/%m/%Y %H%M")
                if crew_avail.get(slot_key_to_check, False):
                    entry["crew"].append(crew["name"])

    return list(appliance_dict.values())


def _get_table_and_header(grid_html):
    """
    Extract the main table and header row from the grid HTML.
    Returns (table, header_row) or (None, None) if not found.
    """
    soup = BeautifulSoup(grid_html, "html.parser")
    table = soup.find("table", attrs={"id": "gridAvail"})
    if not table:
        return None, None
    rows = table.find_all("tr", recursive=False)
    for tr in rows:
        if not isinstance(tr, Tag):
            continue
        tr_class = tr.attrs.get("class", [])
        if isinstance(tr_class, list) and "gridheader" in tr_class:
            return table, tr
    return table, None


def _get_slot_datetimes(availability: dict) -> list[tuple[dt, bool]]:
    """Converts a dictionary of availability slots to a sorted list of (datetime, bool) tuples."""
    slot_datetimes = []
    for slot, is_avail in availability.items():
        try:
            slot_dt = dt.strptime(slot, "%d/%m/%Y %H%M")
            slot_datetimes.append((slot_dt, is_avail))
        except (ValueError, TypeError):
            continue
    slot_datetimes.sort()
    return slot_datetimes


def _extract_time_slots(header_row):
    """
    Extract time slot labels from the header row (skipping first 5 columns).
    """
    header_cells = header_row.find_all("td")
    # Extract all time slot labels after the first header columns (skip only non-time columns)
    # Find the first cell that looks like a time (e.g., '0000', '0015', etc.)
    import re

    slot_start_idx = 0
    for i, cell in enumerate(header_cells):
        text = cell.get_text(strip=True)
        if re.match(r"^\d{4}$", text):
            slot_start_idx = i
            break
    return [cell.get_text(strip=True) for cell in header_cells[slot_start_idx:]]


def _extract_crew_availability(date, table, time_slots):
    """
    Extract crew availability for all rows in the table.
    Returns a dict with crew_availability list.
    """
    from datetime import datetime as dt

    date_prefix = _normalize_date(date)
    now = dt.now()
    crew_data = []
    for tr in _extract_crew_rows(table):
        crew_data.append(_parse_crew_row(tr, time_slots, date_prefix, now))
    return {"crew_availability": crew_data}


def _extract_crew_rows(table):
    """
    Return all crew rows (tr) with class 'employee'.
    """
    return [
        tr
        for tr in table.find_all("tr")
        if isinstance(tr.get("class", []), list) and "employee" in tr.get("class", [])
    ]


def _parse_crew_row(tr, time_slots, date_prefix, now):
    tds = tr.find_all("td")
    name = tds[0].get_text(strip=True)
    role = tds[0].attrs.get("data-role")
    if not role and len(tds) > 1:
        role = tds[1].get_text(strip=True)
    skills = None

    # Find the index of the first time slot column by looking for the 'skillCol'
    # and starting from the next cell.
    slot_start_idx = -1
    for i, td in enumerate(tds):
        if "skillCol" in td.get("class", []):
            skills = td.get_text(strip=True)
            slot_start_idx = i + 1
            break

    # Fallback for rows that might not have a skillCol
    if slot_start_idx == -1:
        # A reasonable guess is that the slots start after the 4th cell.
        # This is brittle but better than failing completely.
        slot_start_idx = 4

    avail_cells = tds[slot_start_idx : slot_start_idx + len(time_slots)]

    availability = _parse_availability_cells(
        avail_cells, time_slots, date_prefix, entity_type="crew"
    )
    slot_datetimes = _get_slot_datetimes(availability)
    summary = _calculate_availability_summary(slot_datetimes, now)

    from logging_config import get_logger

    logger = get_logger()
    logger.debug(
        f"Parsed crew row for {name}: {len(availability)} slots found, summary: {summary}"
    )

    return {
        "name": name,
        "role": role,
        "skills": skills,
        "availability": availability,
        **summary,
    }


def parse_appliance_availability(grid_html, date=None):
    """
    Parse the appliance availability table and return a dict of slot -> bool (True=available, False=unavailable).
    Args:
        grid_html (str): HTML string of the gridAvail table
        date (str): booking date (optional)
    Returns:
        dict: { 'date': date, 'appliance_availability': { slot: bool, ... } }
    """
    from bs4 import BeautifulSoup, Tag

    log_debug("appliance", "Parsing appliance availability...")
    soup = BeautifulSoup(grid_html, "html.parser")
    tables = [t for t in soup.find_all("table") if isinstance(t, Tag)]
    log_debug("appliance", f"Found {len(tables)} tables.")
    appliance_table = None
    for table_idx, table in enumerate(tables):
        trs = [
            tr for tr in table.find_all("tr", recursive=False) if isinstance(tr, Tag)
        ]
        for idx, tr in enumerate(trs):
            tds = [
                td for td in tr.find_all("td", recursive=False) if isinstance(td, Tag)
            ]
            if (
                tds
                and tds[0].get_text(strip=True).lower() == "appliances"
                and tds[0].get("colspan") == "5"
            ):
                log_debug(
                    "appliance",
                    f"Found 'Appliances' header in table {table_idx}, row {idx}.",
                )
                appliance_table = table
                header_row_idx = idx
                break
        if appliance_table:
            break
    if not appliance_table:
        log_debug("appliance", "No appliance table found.")
        return {}
    trs = [
        tr
        for tr in appliance_table.find_all("tr", recursive=False)
        if isinstance(tr, Tag)
    ]
    time_header_row = None
    for i in range(len(trs)):
        tds = [
            td for td in trs[i].find_all("td", recursive=False) if isinstance(td, Tag)
        ]
        if (
            tds
            and tds[0].get_text(strip=True).lower() == "appliances"
            and tds[0].get("colspan") == "5"
        ):
            if i + 1 < len(trs):
                time_header_row = trs[i + 1]
                log_debug("appliance", f"Found time header row at index {i+1}.")
            break
    if not time_header_row:
        log_debug("appliance", "No time header row found after 'Appliances' header.")
        return {}
    time_header_cells = [
        cell for cell in time_header_row.find_all("td") if isinstance(cell, Tag)
    ]
    # Extract slot times from the title attribute, e.g., 'P22P6 (0000 - 0015) Available'
    import re

    time_slots = []
    for cell in time_header_cells[1:]:
        title = cell.get("title")
        if not isinstance(title, str):
            title = ""
        match = re.search(r"\((\d{4}) - \d{4}\)", title)
        if match:
            slot_time = match.group(1)
            time_slots.append(slot_time)
        else:
            time_slots.append("")
    appliance_row = None
    for tr_idx, tr in enumerate(trs):
        tds = [td for td in tr.find_all("td", recursive=False) if isinstance(td, Tag)]
        if (
            tds
            and tds[0].get_text(strip=True) == "P22P6"
            and tds[0].get("colspan") == "5"
        ):
            log_debug("appliance", f"Found P22P6 row at index {tr_idx}.")
            appliance_row = tr
            break
    date_prefix = _normalize_date(date)
    availability = {}
    if not appliance_row:
        for slot in time_slots:
            slot_key = f"{date_prefix} {slot}"
            availability[slot_key] = False
    else:
        tds = [
            td
            for td in appliance_row.find_all("td", recursive=False)
            if isinstance(td, Tag)
        ]
        # The slot cells start after the first <td colspan=5>
        avail_cells = tds[1:]
        availability = _parse_availability_cells(
            avail_cells, time_slots, date_prefix, entity_type="appliance"
        )

    result = {
        "availability": availability,
    }
    # Extract appliance name from the row
    appliance_name = None
    from bs4 import Tag

    if appliance_row:
        tds = [
            td
            for td in appliance_row.find_all("td", recursive=False)
            if isinstance(td, Tag)
        ]
        for td in tds:
            if (
                td.has_attr("colspan")
                and td["colspan"] == "5"
                and td.get_text(strip=True)
            ):
                appliance_name = td.get_text(strip=True)
                break
    if not appliance_name:
        appliance_name = "UNKNOWN"
    # Always wrap in dict keyed by appliance name
    return {appliance_name: result}


def aggregate_crew_availability(daily_crew_lists):
    """
    Aggregate crew availability across multiple days, calculate next_available, next_available_until, available_now, available_for.
    Args:
        daily_crew_lists: list of lists of crew dicts (from parse_grid_html)
    Returns:
        crew_list: list of merged crew dicts with status fields
    """
    from datetime import datetime as dt

    crew_dict = {}
    from logging_config import get_logger

    logger = get_logger()
    logger.debug(
        f"Aggregating crew availability from {len(daily_crew_lists)} daily lists."
    )
    for crew_list in daily_crew_lists:
        for crew in crew_list:
            name = crew["name"]
            if name not in crew_dict:
                crew_dict[name] = {"name": name, "availability": {}, "_all_slots": []}
            for slot, avail in crew["availability"].items():
                crew_dict[name]["availability"][slot] = avail
                crew_dict[name]["_all_slots"].append((slot, avail))
    now = dt.now()
    logger.debug(f"Aggregated into {len(crew_dict)} unique crew members.")
    for crew in crew_dict.values():
        slot_tuples = []
        for slot, avail in crew["_all_slots"]:
            try:
                slot_dt = dt.strptime(slot, "%d/%m/%Y %H%M")
                slot_tuples.append((slot_dt, avail))
            except Exception:
                continue
        slot_tuples.sort()

        summary = _calculate_availability_summary(slot_tuples, now)
        crew.update(summary)
        logger.debug(
            f"Calculated summary for {crew['name']}: available_now={summary['available_now']}, next_available={summary['next_available']}"
        )

        del crew["_all_slots"]
    return list(crew_dict.values())


import json

# parse_grid.py: provides parse_grid_html(grid_html, date=None)
from bs4 import BeautifulSoup, Tag


def parse_grid_html(grid_html, date=None):
    """
    Parse the grid HTML and return structured crew and appliance availability data.
    Args:
        grid_html (str): HTML string of the gridAvail table
        date (str): booking date (optional)
    Returns:
        dict: { 'date': date, 'crew_availability': [...], 'appliance_availability': {...} }
    """

    table, header_row = _get_table_and_header(grid_html)
    crew_result = {"date": date, "crew_availability": []}
    if table and header_row:
        time_slots = _extract_time_slots(header_row)
        crew_result = _extract_crew_availability(date, table, time_slots)
        crew_result["date"] = date
    appliance_result = parse_appliance_availability(grid_html, date)
    merged = {"date": date}
    merged["crew_availability"] = crew_result.get("crew_availability", [])
    merged["appliance_availability"] = appliance_result
    return merged


def _parse_availability_cells(avail_cells, time_slots, date_prefix, entity_type="crew"):
    """
    Parse availability cells for a crew or appliance row.
    - For 'crew', availability is the default state (no background style).
    - For 'appliance', availability is explicitly marked by a green background.
    """
    availability = {}
    for i, cell in enumerate(avail_cells):
        slot = time_slots[i]
        slot_key = f"{date_prefix} {slot}"

        style = cell.get("style", "")
        is_available = False  # Default to not available

        if entity_type == "crew":
            # For crew, a slot is available if it does NOT have a background-color style.
            # The presence of 'background-color' indicates a special state (off, etc.).
            if isinstance(style, str) and "background-color" in style.lower():
                is_available = False
            else:
                is_available = True
        elif entity_type == "appliance":
            # For appliances, a slot is available if it has the specific green background color.
            if isinstance(style, str):
                style_str = style.replace(" ", "").lower()
                if "background-color:#009933" in style_str:
                    is_available = True

        availability[slot_key] = is_available
    return availability


def _normalize_date(date):
    """
    Normalize date to dd/mm/yyyy format, or return as-is if not possible.
    """
    from datetime import datetime as dt

    try:
        date_obj = dt.strptime(date, "%d/%m/%Y")
        return date_obj.strftime("%d/%m/%Y")
    except Exception:
        return date or ""
