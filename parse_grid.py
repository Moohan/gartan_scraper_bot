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
    for crew_list in daily_crew_lists:
        for crew in crew_list:
            name = crew["name"]
            if name not in crew_dict:
                crew_dict[name] = {"name": name, "availability": {}, "_all_slots": []}
            for slot, avail in crew["availability"].items():
                crew_dict[name]["availability"][slot] = avail
                crew_dict[name]["_all_slots"].append((slot, avail))
    now = dt.now()
    for crew in crew_dict.values():
        slot_tuples = []
        for slot, avail in crew["_all_slots"]:
            try:
                slot_dt = dt.strptime(slot, "%d/%m/%Y %H%M")
                slot_tuples.append((slot_dt, avail))
            except Exception:
                continue
        slot_tuples.sort()
        next_avail = None
        next_avail_until = None
        available_now = False
        available_for = None
        for idx, (slot_dt, avail) in enumerate(slot_tuples):
            if slot_dt >= now:
                if avail:
                    if idx == 0 and slot_dt <= now:
                        available_now = True
                    elif slot_dt <= now:
                        available_now = True
                    next_avail = slot_dt.strftime("%d/%m/%Y %H:%M")
                    available_hours = None
                    for j in range(idx + 1, len(slot_tuples)):
                        next_dt, next_avail_val = slot_tuples[j]
                        hours_since_avail = (next_dt - slot_dt).total_seconds() / 3600.0
                        if not next_avail_val:
                            next_avail_until = next_dt.strftime("%d/%m/%Y %H:%M")
                            available_hours = hours_since_avail
                            break
                        if hours_since_avail >= 72:
                            available_hours = ">72"
                            break
                    if available_hours is None:
                        if len(slot_tuples) > idx + 1:
                            last_dt, last_avail = slot_tuples[-1]
                            hours_since_avail = (
                                last_dt - slot_dt
                            ).total_seconds() / 3600.0
                            if last_avail and hours_since_avail >= 72:
                                available_hours = ">72"
                    if available_hours == ">72":
                        available_for = ">72h"
                    elif isinstance(available_hours, (int, float)):
                        available_for = f"{round(available_hours, 2)}h"
                    else:
                        available_for = None
                    break
        crew["available_now"] = available_now
        crew["next_available"] = next_avail
        crew["next_available_until"] = next_avail_until
        crew["available_for"] = available_for
        del crew["_all_slots"]
    return list(crew_dict.values())


# parse_grid.py: provides parse_grid_html(grid_html, date=None)
from bs4 import BeautifulSoup, Tag
import json


def parse_grid_html(grid_html, date=None):
    """
    Parse the grid HTML and return structured crew availability data.
    Args:
        grid_html (str): HTML string of the gridAvail table
        date (str): booking date (optional)
    Returns:
        dict: { 'date': date, 'crew_availability': [ { 'name': ..., 'availability': { time: bool, ... }, 'next_available': ... }, ... ] }
    """
    table, header_row = _get_table_and_header(grid_html)
    if not table or not header_row:
        return {"date": date, "crew_availability": []}
    time_slots = _extract_time_slots(header_row)
    result = _extract_crew_availability(date, table, time_slots)
    # _extract_crew_availability always returns a dict
    result["date"] = date  # type: ignore
    return result


def _get_table_and_header(grid_html):
    """
    Extract the main table and header row from the grid HTML.
    Returns (table, header_row) or (None, None) if not found.
    """
    soup = BeautifulSoup(grid_html, "html.parser")
    table = soup.find("table", attrs={"id": "gridAvail"})
    if not table:
        return None, None
    from bs4 import Tag

    # Only iterate over direct tr children (Tag elements)
    # BeautifulSoup's table is always Tag if not None, so find_all is safe
    rows = table.find_all("tr", recursive=False)  # type: ignore[attr-defined]
    for tr in rows:
        if not isinstance(tr, Tag):
            continue
        tr_class = tr.attrs.get("class", [])
        if isinstance(tr_class, list) and "gridheader" in tr_class:
            return table, tr
    return table, None


def _extract_time_slots(header_row):
    """
    Extract time slot labels from the header row (skipping first 5 columns).
    """
    header_cells = header_row.find_all("td")
    return [cell.get_text(strip=True) for cell in header_cells[5:]]


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
    """
    Parse a single crew row and return dict with name, availability, and next_available.
    """
    name = tr.get("data-name", "").strip()
    tds = tr.find_all("td")
    avail_cells = tds[5:]
    availability = _parse_availability_cells(avail_cells, time_slots, date_prefix)
    slot_datetimes = _get_slot_datetimes(
        avail_cells, time_slots, date_prefix, availability
    )
    next_avail = _find_next_available(slot_datetimes, now)
    return {"name": name, "availability": availability, "next_available": next_avail}


def _parse_availability_cells(avail_cells, time_slots, date_prefix):
    """
    Parse availability cells for a crew row. Returns a dict mapping slot_key to bool.
    """
    availability = {}
    for i, cell in enumerate(avail_cells):
        val = cell.get_text(strip=True)
        slot = time_slots[i]
        slot_key = f"{date_prefix} {slot}"
        availability[slot_key] = val == ""
    return availability


def _get_slot_datetimes(avail_cells, time_slots, date_prefix, availability):
    """
    Return list of (datetime, is_available) for each slot.
    """
    from datetime import datetime as dt

    slot_datetimes = []
    for i, cell in enumerate(avail_cells):
        slot = time_slots[i]
        slot_key = f"{date_prefix} {slot}"
        try:
            slot_dt = dt.strptime(f"{date_prefix} {slot}", "%d/%m/%Y %H%M")
            slot_datetimes.append((slot_dt, availability[slot_key]))
        except Exception:
            pass
    return slot_datetimes


def _find_next_available(slot_datetimes, now):
    """
    Find the next available slot after 'now'.
    Returns 'now' if available at the current time, else the next available slot as a string, or None.
    """
    for slot_dt, is_avail in slot_datetimes:
        if slot_dt >= now and is_avail:
            if slot_dt <= now:
                return "now"
            return slot_dt.strftime("%d/%m/%Y %H:%M")
    return None


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
