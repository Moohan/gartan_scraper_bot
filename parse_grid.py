import logging
from datetime import datetime as dt
from utils import log_debug


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
    for appliance, entry in appliance_dict.items():
        availability = entry["availability"]
        slot_tuples = []
        now = dt.now()
        for slot, avail in availability.items():
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
        next_avail_idx = None
        next_avail_end_idx = None
        for idx, (slot_dt, avail) in enumerate(slot_tuples):
            if slot_dt >= now:
                if avail:
                    if idx == 0 and slot_dt <= now:
                        available_now = True
                    elif slot_dt <= now:
                        available_now = True
                    next_avail = slot_dt.strftime("%d/%m/%Y %H:%M")
                    next_avail_idx = idx
                    available_hours = None
                    next_avail_until = None
                    next_avail_end_idx = None
                    last_true_dt = slot_dt
                    for j in range(idx + 1, len(slot_tuples)):
                        next_dt, next_avail_val = slot_tuples[j]
                        if next_avail_val:
                            last_true_dt = next_dt
                            if (last_true_dt - slot_dt).total_seconds() / 3600.0 >= 72:
                                available_hours = ">72"
                                next_avail_end_idx = j
                                break
                        else:
                            next_avail_until = next_dt.strftime("%d/%m/%Y %H:%M")
                            next_avail_end_idx = j
                            available_hours = (
                                last_true_dt - slot_dt
                            ).total_seconds() / 3600.0
                            break
                    if available_hours is None:
                        if len(slot_tuples) > idx + 1:
                            last_dt, last_avail = slot_tuples[-1]
                            if last_avail:
                                available_hours = (
                                    ">72"
                                    if (last_dt - slot_dt).total_seconds() / 3600.0
                                    >= 72
                                    else (last_dt - slot_dt).total_seconds() / 3600.0
                                )
                                next_avail_end_idx = len(slot_tuples) - 1
                    if available_hours == ">72":
                        available_for = ">72h"
                    elif isinstance(available_hours, (int, float)):
                        available_for = f"{round(available_hours, 2)}h"
                    else:
                        available_for = None
                    break
        entry["available_now"] = available_now
        entry["next_available"] = next_avail
        entry["next_available_until"] = next_avail_until
        entry["available_for"] = available_for
        # Add crew available during the next available period
        entry["crew"] = []
        if crew_list_agg and next_avail_idx is not None:
            # Determine the slot keys for the next available period
            # Use string slot keys for period_slots
            if next_avail_end_idx is not None:
                period_slots = [
                    slot_tuples[i][0].strftime("%d/%m/%Y %H%M")
                    for i in range(next_avail_idx, next_avail_end_idx)
                ]
            else:
                period_slots = [
                    slot_tuples[i][0].strftime("%d/%m/%Y %H%M")
                    for i in range(next_avail_idx, len(slot_tuples))
                ]
            log_debug(
                "appliance",
                f"Appliance '{appliance}' next available period slots: {period_slots}",
            )
            # Only require crew to be available for slots where the appliance is available
            for crew in crew_list_agg:
                crew_avail = crew.get("availability", {})
                available_for_all = []
                for slot in period_slots:
                    if availability.get(slot, False):
                        available_for_all.append(crew_avail.get(slot, False))
                log_debug(
                    "appliance",
                    f"Crew '{crew['name']}' available for appliance-available slots: {available_for_all}",
                )
                if available_for_all and all(available_for_all):
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
    for td in tds:
        if "skillCol" in td.get("class", []):
            skills = td.get_text(strip=True)
            break
    import re

    slot_start_idx = 0
    for i, cell in enumerate(tds):
        text = cell.get_text(strip=True)
        if re.match(r"^\d{4}$", text):
            slot_start_idx = i
            break
    avail_cells = tds[slot_start_idx : slot_start_idx + len(time_slots)]
    availability = _parse_availability_cells(avail_cells, time_slots, date_prefix)
    slot_datetimes = _get_slot_datetimes(
        avail_cells, time_slots, date_prefix, availability
    )
    next_avail = _find_next_available(slot_datetimes, now)
    return {
        "name": name,
        "role": role,
        "skills": skills,
        "availability": availability,
        "next_available": next_avail,
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
    log_debug("appliance", "First 10 time header cells raw HTML:")
    for i, cell in enumerate(time_header_cells[:10]):
        log_debug("appliance", f"time_header_cells[{i}]: {str(cell)}")
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
    log_debug(
        "appliance",
        f"Extracted time_slots: {time_slots[:10]} ... total {len(time_slots)}",
    )
    log_debug("appliance", f"Extracted {len(time_slots)} time slots.")
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
    if not appliance_row:
        log_debug("appliance", "No P22P6 row found.")
    else:
        log_debug("appliance", "Parsing slot cells for P22P6...")
    date_prefix = _normalize_date(date)
    if appliance_row and time_slots:
        log_debug(
            "appliance",
            f"Will generate slot keys like: '{date_prefix} {time_slots[0]}' ... '{date_prefix} {time_slots[min(4, len(time_slots)-1)]}'",
        )
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
        for i, slot in enumerate(time_slots):
            slot_key = f"{date_prefix} {slot}"
            is_available = False
            if i < len(avail_cells):
                cell = avail_cells[i]
                style = cell.get("style", "")
                if isinstance(style, str):
                    style_str = style.replace(" ", "").lower()
                else:
                    style_str = ""
                if "background-color:#009933" in style_str:
                    is_available = True
                elif "background-color:#323232" in style_str:
                    is_available = False
            availability[slot_key] = is_available

    # Calculate available_now, next_available, next_available_until, available_for
    from datetime import datetime as dt

    slot_tuples = []
    now = dt.now()
    for slot, avail in availability.items():
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
                        hours_since_avail = (last_dt - slot_dt).total_seconds() / 3600.0
                        if last_avail and hours_since_avail >= 72:
                            available_hours = ">72"
                if available_hours == ">72":
                    available_for = ">72h"
                elif isinstance(available_hours, (int, float)):
                    available_for = f"{round(available_hours, 2)}h"
                else:
                    available_for = None
                break
    result = {
        "availability": availability,
        "available_now": available_now,
        "next_available": next_avail,
        "next_available_until": next_avail_until,
        "available_for": available_for,
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
        log_debug("crew", f"Crew {crew['name']} slot_tuples: {slot_tuples}")
        log_debug("crew", f"Now: {now}")
        next_avail = None
        next_avail_until = None
        available_now = False
        available_for = None

        # Find the slot that covers 'now' (the first slot with slot_dt > now, or the last slot before now)
        covering_idx = None
        for idx, (slot_dt, avail) in enumerate(slot_tuples):
            if slot_dt > now:
                covering_idx = idx - 1 if idx > 0 else 0
                break
        if covering_idx is None and slot_tuples:
            covering_idx = len(slot_tuples) - 1
        if covering_idx is not None and slot_tuples:
            slot_dt, avail = slot_tuples[covering_idx]
            log_debug(
                "crew",
                f"Slot covering now: {slot_dt} avail={avail} (idx={covering_idx})",
            )
            if avail:
                available_now = True

        # Find next available run (first slot >= now that is available)
        for idx, (slot_dt, avail) in enumerate(slot_tuples):
            log_debug("crew", f"Checking slot {slot_dt} avail={avail} (idx={idx})")
            if slot_dt >= now and avail:
                next_avail = slot_dt.strftime("%d/%m/%Y %H:%M")
                log_debug(
                    "crew", f"Found next_available for {crew['name']}: {next_avail}"
                )
                # Extend next_available_until to the end of the contiguous available run
                last_true_dt = slot_dt
                for j in range(idx + 1, len(slot_tuples)):
                    next_dt, next_avail_val = slot_tuples[j]
                    log_debug("crew", f"  Extending: {next_dt} avail={next_avail_val}")
                    if next_avail_val:
                        last_true_dt = next_dt
                        if (last_true_dt - slot_dt).total_seconds() / 3600.0 >= 72:
                            available_for = ">72h"
                            next_avail_until = None
                            break
                    else:
                        next_avail_until = next_dt.strftime("%d/%m/%Y %H:%M")
                        available_for = f"{round((last_true_dt - slot_dt).total_seconds() / 3600.0, 2)}h"
                        log_debug(
                            "crew",
                            f"  next_available_until for {crew['name']}: {next_avail_until}",
                        )
                        break
                else:
                    # If we never hit a False, the run goes to the end of the slots
                    if last_true_dt != slot_dt:
                        available_for = f"{round((last_true_dt - slot_dt).total_seconds() / 3600.0, 2)}h"
                        next_avail_until = None
                    else:
                        available_for = "0h"
                        next_avail_until = None
                break

        log_debug(
            "crew",
            f"Final for {crew['name']}: available_now={available_now}, next_available={next_avail}, next_available_until={next_avail_until}, available_for={available_for}",
        )
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


def _parse_availability_cells(avail_cells, time_slots, date_prefix):
    """
    Parse availability cells for a crew row. Returns a dict mapping slot_key to bool.
    """
    availability = {}
    for i, cell in enumerate(avail_cells):
        slot = time_slots[i]
        slot_key = f"{date_prefix} {slot}"
        # Mark as available only if cell has explicit attribute indicating availability (e.g., data-comment="1" or similar)
        # Otherwise, mark as unavailable
        if cell.has_attr("data-comment"):
            if cell["data-comment"] == "1":
                availability[slot_key] = True
            else:
                availability[slot_key] = False
        else:
            # If no data-comment attribute, treat as unavailable
            availability[slot_key] = False
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
