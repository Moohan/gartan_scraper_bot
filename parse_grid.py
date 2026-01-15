"""HTML parsing and availability aggregation utilities.

Transforms raw schedule grid HTML into structured availability blocks for
crew and appliances, plus helper summarization (next available windows etc.).
"""

from datetime import datetime as dt
from typing import Any, Dict, List, Optional, Tuple, TypedDict, Union

from bs4 import BeautifulSoup, NavigableString, Tag  # type: ignore

from utils import log_debug

# Type aliases for clarity
GridElement = Union[Tag, NavigableString]
GridTable = Tag
GridCell = Tag
AvailabilityDict = Dict[str, Union[str, List[str], Dict[str, bool]]]
TimeBlock = Dict[str, Union[str, List[str]]]


class GridResult(TypedDict):
    """Structured result from grid HTML parsing."""

    date: Optional[str]
    crew_availability: List[AvailabilityDict]
    appliance_availability: Dict[str, AvailabilityDict]
    skills_data: Dict[str, Dict[str, int]]


def safe_find_one(element: Tag, name: str, **kwargs) -> Optional[Tag]:
    """Safely find one element, ensuring it is a Tag."""
    result = element.find(name, **kwargs)
    return result if isinstance(result, Tag) else None


def safe_find_all(element: Union[Tag, BeautifulSoup], name: str, **kwargs) -> List[Tag]:
    """Safely find all elements, ensuring they are Tags."""
    results = element.find_all(name, **kwargs)
    return [r for r in results if isinstance(r, Tag)]


def _find_next_availability_block(
    slot_tuples: list[tuple[dt, bool]], start_idx: int, now: dt
) -> tuple[Optional[dt], Optional[dt], Optional[str]]:
    """Find next block of continuous availability from given index."""
    if start_idx >= len(slot_tuples):
        return None, None, None

    next_avail = None
    available_for = None

    for idx in range(start_idx, len(slot_tuples)):
        slot_dt, avail = slot_tuples[idx]
        if slot_dt >= now and avail:
            next_avail = slot_dt
            last_true_dt = slot_dt
            next_avail_until_dt = None

            # Look ahead for continuous availability
            for j in range(idx + 1, len(slot_tuples)):
                next_dt, next_avail_val = slot_tuples[j]
                if next_avail_val:
                    last_true_dt = next_dt
                    if (last_true_dt - slot_dt).total_seconds() / 3600.0 >= 72:
                        break  # Stop if we have a 72h+ block
                else:
                    next_avail_until_dt = next_dt
                    break

            # Calculate duration
            duration_hours = (last_true_dt - slot_dt).total_seconds() / 3600.0 + 0.25
            available_for = (
                ">72h" if duration_hours >= 72 else f"{round(duration_hours, 2)}h"
            )

            return next_avail, next_avail_until_dt, available_for

    return None, None, None


def _calculate_current_availability(
    slot_tuples: list[tuple[dt, bool]], now: dt
) -> tuple[bool, int]:
    """Check if available right now and get current slot index."""
    covering_idx = None
    for idx, (slot_dt, _) in enumerate(slot_tuples):
        if slot_dt > now:
            covering_idx = idx - 1 if idx > 0 else 0
            break

    if covering_idx is None and slot_tuples:
        covering_idx = len(slot_tuples) - 1

    available_now = False
    if covering_idx is not None:
        _, avail = slot_tuples[covering_idx]
        available_now = avail

    return available_now, covering_idx or 0


def _calculate_availability_summary(
    slot_tuples: list[tuple[dt, bool]], now: dt
) -> dict:
    """Calculates availability summary fields from sorted (datetime, available) tuples."""
    available_now, current_idx = _calculate_current_availability(slot_tuples, now)
    next_avail, next_avail_until_dt, available_for = _find_next_availability_block(
        slot_tuples, current_idx, now
    )

    return {
        "available_now": available_now,
        "next_available": next_avail.strftime("%d/%m/%Y %H:%M") if next_avail else None,
        "next_available_until": (
            next_avail_until_dt.strftime("%d/%m/%Y %H:%M")
            if next_avail_until_dt
            else None
        ),
        "available_for": available_for,
    }


def _merge_appliance_data(
    appliance_dict: Dict[str, Dict], appliance: str, data: Dict
) -> None:
    """Merge availability data for a single appliance."""
    if appliance not in appliance_dict:
        appliance_dict[appliance] = {"appliance": appliance, "availability": {}}
    appliance_dict[appliance]["availability"].update(data.get("availability", {}))


def aggregate_appliance_availability(
    daily_appliance_lists: List[Dict[str, AvailabilityDict]],
    crew_list_agg: Optional[List[Dict[str, Any]]] = None,
) -> List[AvailabilityDict]:
    """Aggregate appliance availability across multiple days."""
    appliance_dict = {}
    # Merge all slot availabilities for each appliance
    for daily in daily_appliance_lists:
        for appliance, data in daily.items():
            _merge_appliance_data(appliance_dict, appliance, data)

    # Now recalculate summary fields for each appliance
    now = dt.now()
    for entry in appliance_dict.values():
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

        # Initialize empty crew list
        entry["crew"] = []

    return list(appliance_dict.values())


def _get_slot_datetimes(availability: dict) -> list[tuple[dt, bool]]:
    """Convert dict of slots to sorted list of datetime tuples."""
    slot_datetimes = []
    for slot, is_avail in availability.items():
        try:
            slot_dt = dt.strptime(slot, "%d/%m/%Y %H%M")
            slot_datetimes.append((slot_dt, is_avail))
        except (ValueError, TypeError):
            continue
    slot_datetimes.sort()
    return slot_datetimes


def _extract_time_slots(header_row: Tag) -> list[str]:
    """Extract time slot labels."""
    header_cells = header_row.find_all("td")
    import re

    slot_start_idx = 0
    for i, cell in enumerate(header_cells):
        text = cell.get_text(strip=True)
        if re.match(r"^\d{4}$", text):
            slot_start_idx = i
            break
    return [cell.get_text(strip=True) for cell in header_cells[slot_start_idx:]]


def _extract_crew_availability(
    date: Optional[str], table: Tag, time_slots: List[str]
) -> Dict[str, list]:
    """Extract crew availability."""
    date_prefix = _normalize_date(date)
    now = dt.now()
    crew_data = []
    for tr in _extract_crew_rows(table):
        crew_data.append(_parse_crew_row(tr, time_slots, date_prefix, now))
    return {"crew_availability": crew_data}


def _extract_crew_rows(table: Tag) -> List[Tag]:
    """Get crew rows with class 'employee'."""
    return [
        tr
        for tr in safe_find_all(table, "tr")
        if tr.attrs.get("class") and "employee" in tr.attrs["class"]
    ]


def _parse_crew_row(
    tr: Tag, time_slots: List[str], date_prefix: str, now: dt
) -> Dict[str, Any]:
    """Parse crew row into structured data."""
    tds = safe_find_all(tr, "td")

    # Parse crew metadata
    name = tds[0].get_text(strip=True)
    role = tds[1].get_text(strip=True) if len(tds) > 1 else None
    contract_hours = tds[2].get_text(strip=True) if len(tds) > 2 else None
    skills = None

    # Find skill column
    slot_start_idx = -1
    for i, td in enumerate(tds):
        if td.attrs.get("class") and "skillCol" in td.attrs["class"]:
            skills = td.get_text(strip=True).replace("&nbsp;", " ").strip()
            slot_start_idx = i + 1
            break

    if slot_start_idx == -1:
        slot_start_idx = 4

    avail_cells = tds[slot_start_idx : slot_start_idx + len(time_slots)]
    availability = _parse_availability_cells(
        avail_cells, time_slots, date_prefix, entity_type="crew"
    )
    slot_datetimes = _get_slot_datetimes(availability)
    summary = _calculate_availability_summary(slot_datetimes, now)

    log_debug(
        "crew",
        f"Parsed crew row for {name}: {len(availability)} slots, summary: {summary}",
    )

    return {
        "name": name,
        "role": role,
        "contract_hours": contract_hours,
        "skills": skills,
        "availability": availability,
        **summary,
    }


def _find_appliance_name(appliance_row: Optional[Tag]) -> str:
    """Extract appliance name from row."""
    if not appliance_row:
        return "UNKNOWN"

    # Preferred: look for a cell with colspan=5 (typical in full tables)
    name_cell = safe_find_one(appliance_row, "td", attrs={"colspan": "5"})
    if name_cell and name_cell.get_text(strip=True):
        return name_cell.get_text(strip=True)

    # Fallback: use the first td text (covers simplified test HTML)
    first_td = safe_find_one(appliance_row, "td")
    if first_td and first_td.get_text(strip=True):
        return first_td.get_text(strip=True)

    return "UNKNOWN"


def _find_appliance_table(soup: BeautifulSoup) -> Optional[Tag]:
    """Find the appliance table in HTML content."""
    tables = safe_find_all(soup, "table")
    for table_idx, table in enumerate(tables):
        for idx, tr in enumerate(safe_find_all(table, "tr", recursive=False)):
            tds = safe_find_all(tr, "td", recursive=False)
            if (
                tds
                and tds[0].get_text(strip=True).lower() == "appliances"
                and tds[0].get("colspan") == "5"
            ):
                log_debug(
                    "appliance",
                    f"Found 'Appliances' header in table {table_idx}, row {idx}.",
                )
                return table
    return None


def _find_time_header_row(table: Tag) -> Optional[Tag]:
    """Find time header row in appliance table."""
    trs = safe_find_all(table, "tr", recursive=False)
    for i in range(len(trs)):
        tds = safe_find_all(trs[i], "td", recursive=False)
        if (
            tds
            and tds[0].get_text(strip=True).lower() == "appliances"
            and tds[0].get("colspan") == "5"
        ):
            if i + 1 < len(trs):
                log_debug("appliance", f"Found time header row at index {i+1}.")
                return trs[i + 1]
    return None


def _extract_appliance_time_slots(time_header_row: Tag) -> list[str]:
    """Extract time slots from appliance header row."""
    time_slots = []
    for cell in safe_find_all(time_header_row, "td")[1:]:
        slot = parse_time_slot(cell)
        if slot:
            time_slots.append(slot)
    return time_slots


def _aggregate_time_blocks(all_availabilities: Dict[str, bool]) -> List[Dict[str, Any]]:
    """Convert timestamp dictionary into efficient time blocks."""
    all_times = sorted(all_availabilities.keys())
    if not all_times:  # No data found
        return []


def _find_rules_table(soup: BeautifulSoup) -> Tuple[Optional[Tag], int]:
    """Find the rules table and header index."""
    for table in safe_find_all(soup, "table"):
        for i, row in enumerate(safe_find_all(table, "tr")):
            cells = safe_find_all(row, "td")
            if cells and cells[0].get_text(strip=True) == "Rules":
                return table, i
    return None, -1


def _normalize_date(date: Optional[str]) -> str:
    """Normalize date to dd/mm/yyyy format."""
    if not date:
        return ""

    try:
        date_obj = dt.strptime(str(date), "%d/%m/%Y")
        return date_obj.strftime("%d/%m/%Y")
    except ValueError:
        return str(date)


def _parse_skills_row(
    row: Tag, time_slots: list[str], date_prefix: str
) -> dict[str, int]:
    """Parse a single skill row."""
    cells = safe_find_all(row, "td")
    avail_data = {}

    if len(cells) > len(time_slots):
        for i, time_slot in enumerate(time_slots):
            slot_key = f"{date_prefix} {time_slot}"
            cell_idx = i + 1
            if cell_idx < len(cells):
                avail_text = cells[cell_idx].get_text(strip=True)
                try:
                    avail_count = int(avail_text) if avail_text.isdigit() else 0
                    avail_data[slot_key] = avail_count
                except ValueError:
                    avail_data[slot_key] = 0

    return avail_data


def _find_skills_table(soup: BeautifulSoup) -> Optional[tuple[Tag, int]]:
    """Find skills/rules table and header row index."""
    for table in safe_find_all(soup, "table"):
        for i, row in enumerate(safe_find_all(table, "tr")):
            cells = safe_find_all(row, "td")
            if cells and cells[0].get_text(strip=True).lower() == "rules":
                return table, i
    return None


def _extract_skills_time_slots(header_row: Optional[Tag]) -> list[str]:
    """Extract time slots from skills table header."""
    time_slots = []
    if header_row:
        header_cells = safe_find_all(header_row, "td")[1:]  # Skip first cell
        for cell in header_cells:
            time_text = cell.get_text(strip=True)
            if time_text.isdigit() and len(time_text) == 4:
                time_slots.append(time_text)
    return time_slots


def _parse_skill_row(
    row: Tag, time_slots: List[str], date_prefix: str
) -> Dict[str, int]:
    """Parse a single skill row into time slot availability."""
    cells = safe_find_all(row, "td")[1:]  # Skip skill name column
    availability = {}
    for cell, time_slot in zip(cells, time_slots):
        if not cell or not time_slot:
            continue
        time_key = f"{date_prefix} {time_slot}"
        # For skills, any non-zero count means available
        count_text = cell.get_text(strip=True)
        try:
            count = int(count_text) if count_text else 0
            availability[time_key] = count
        except (ValueError, TypeError):
            availability[time_key] = 0
    return availability


def parse_skills_table(
    soup: BeautifulSoup, date: Optional[str] = None
) -> Dict[str, Dict[str, Any]]:
    """
    Parse skills/rules table for BA, LGV, Total Crew counts.
    - Bolt ⚡: This function now accepts a BeautifulSoup object directly to avoid
    - re-parsing the same HTML, improving performance.
    """
    log_debug("skills", "Parsing skills/rules table...")
    table_match = _find_skills_table(soup)
    if not table_match:
        log_debug("skills", "No rules table found")
        return {}
    table, header_idx = table_match
    rows = safe_find_all(table, "tr")
    if header_idx + 1 >= len(rows):
        log_debug("skills", "No data rows after Rules header")
        return {"skills_availability": {}}
    date_prefix = _normalize_date(date)
    header_row = rows[header_idx + 1]
    time_slots = _extract_skills_time_slots(header_row)
    if not time_slots:
        log_debug("skills", "No valid time slots found")
        return {"skills_availability": {}}
    skills_data = {}
    for row in rows[header_idx + 2 :]:
        cells = safe_find_all(row, "td")
        if len(cells) < 2:
            continue
        skill_name = cells[0].get_text(strip=True)
        if skill_name in ["BA", "LGV", "Total Crew", "MGR"]:
            skill_data = _parse_skill_row(row, time_slots, date_prefix)
            if skill_data:
                skills_data[skill_name] = skill_data
    log_debug("skills", f"Parsed skills data: {skills_data}")
    return {"skills_availability": skills_data}


def _find_p22p6_row(table: Tag) -> Optional[Tag]:
    """Find P22P6 row in appliance table."""
    for tr_idx, tr in enumerate(safe_find_all(table, "tr", recursive=False)):
        tds = safe_find_all(tr, "td", recursive=False)
        if (
            tds
            and tds[0].get_text(strip=True) == "P22P6"
            and tds[0].get("colspan") == "5"
        ):
            log_debug("appliance", f"Found P22P6 row at index {tr_idx}.")
            return tr
    return None


def _parse_appliance_availability_data(
    appliance_row: Optional[Tag], time_slots: List[str], date_prefix: str
) -> Dict[str, bool]:
    """Parse availability data from appliance row."""
    if not appliance_row:
        return {f"{date_prefix} {slot}": False for slot in time_slots if slot}

    tds = safe_find_all(appliance_row, "td", recursive=False)
    avail_cells = tds[1:]
    return _parse_availability_cells(
        avail_cells, time_slots, date_prefix, entity_type="appliance"
    )


def _find_appliance_rows(soup: BeautifulSoup) -> List[Tuple[Tag, Tag]]:
    """Find all appliance header and data rows."""
    appliance_rows = []
    for table in safe_find_all(soup, "table", attrs={"id": "gridAvail"}):
        rows = safe_find_all(table, "tr")
        # Find all appliance headers
        for i, row in enumerate(rows):
            if "Appliances" in row.get_text() and i + 1 < len(rows):
                # The next row is the header, and the one after that is the data
                if i + 2 < len(rows):
                    appliance_rows.append((rows[i + 1], rows[i + 2]))
    # Fallback for the test case structure: check all tables when no id-based table found
    if not appliance_rows:
        for table in safe_find_all(soup, "table"):
            rows = safe_find_all(table, "tr")
            for i, row in enumerate(rows):
                if "P22P6" in row.get_text() and i > 0:
                    appliance_rows.append((rows[i - 1], row))

    return appliance_rows


def parse_appliance_availability(
    soup: BeautifulSoup, date: Optional[str] = None
) -> Dict[str, Dict[str, Any]]:
    """
    Parse appliance availability grid and returns dictionary of time slots with availability.
    - Bolt ⚡: This function now accepts a BeautifulSoup object directly to avoid
    - re-parsing the same HTML, improving performance.
    """
    log_debug("appliance", "Parsing appliance availability grid...")
    appliance_rows = _find_appliance_rows(soup)
    if not appliance_rows:
        log_debug("appliance", "No appliance rows found")
        return {}

    all_appliances = {}
    for header_row, data_row in appliance_rows:
        time_slots = _extract_appliance_time_slots(header_row)
        if not time_slots:
            continue

        appliance_name = _find_appliance_name(data_row)
        if not appliance_name:
            continue

        date_prefix = _normalize_date(date)
        availability_data = _parse_appliance_availability_data(
            data_row, time_slots, date_prefix
        )
        all_appliances[appliance_name] = {"availability": availability_data}

    return all_appliances


def safe_get_text(cell: Optional[Tag]) -> str:
    """Return stripped text for a Tag or empty string otherwise."""
    if isinstance(cell, Tag):
        return cell.get_text(strip=True)
    return ""


def has_available_style(cell: Optional[Tag]) -> bool:
    """Detect the availability style used for appliances (green background)."""
    if not isinstance(cell, Tag):
        return False
    style = cell.get("style", "")
    if not isinstance(style, str):
        return False
    style_str = style.replace(" ", "").lower()
    # Support multiple green shades found in different Gartan versions
    return any(color in style_str for color in ["#009933", "#4ea72e"])


def parse_time_slot(cell: Optional[Tag]) -> str:
    """Parse a time label from a header cell, falling back to text content.

    Returns HHMM like '0900' or empty string on failure.
    """
    if not isinstance(cell, Tag):
        return ""
    title = cell.get("title", "") or ""
    if isinstance(title, str) and "(" in title:
        import re

        match = re.search(r"\((\d{4})", str(title))
        if match:
            return match.group(1)
    text = safe_get_text(cell)
    return text.replace(":", "")


def aggregate_crew_availability(
    daily_crew_lists: List[List[Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    """Aggregate crew availability across multiple days."""
    crew_dict = {}
    log_debug(
        "crew",
        f"Aggregating crew availability from {len(daily_crew_lists)} daily lists.",
    )

    # Merge all crew data
    for crew_list in daily_crew_lists:
        for crew in crew_list:
            name = crew["name"]
            if name not in crew_dict:
                crew_dict[name] = {
                    "name": name,
                    "role": crew.get("role"),
                    "skills": crew.get("skills"),
                    "contract_hours": crew.get("contract_hours"),
                    "availability": {},
                    "_all_slots": [],
                }
            for slot, avail in crew["availability"].items():
                crew_dict[name]["availability"][slot] = avail
                crew_dict[name]["_all_slots"].append((slot, avail))

    # Calculate summaries
    now = dt.now()
    log_debug("crew", f"Aggregated into {len(crew_dict)} unique crew members.")

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
        log_debug(
            "crew",
            f"Calculated summary for {crew['name']}: available_now={summary['available_now']}, next_available={summary['next_available']}",
        )

        del crew["_all_slots"]

    return list(crew_dict.values())


def parse_grid_html(grid_html: str, date: Optional[str] = None) -> GridResult:
    """
    Parse grid HTML into structured crew/appliance availability data.
    - Bolt ⚡: The BeautifulSoup object is created once here and passed to helper
    - functions to avoid redundant parsing, which is a significant performance
    - improvement.
    """
    soup = BeautifulSoup(grid_html, "lxml")

    # Find the main availability table and its header row.
    table = safe_find_one(soup, "table", attrs={"id": "gridAvail"})
    header_row = None
    if table:
        for tr in safe_find_all(table, "tr", recursive=False):
            tr_class = tr.attrs.get("class", [])
            if isinstance(tr_class, list) and "gridheader" in tr_class:
                header_row = tr
                break

    result: GridResult = {
        "date": date,
        "crew_availability": [],
        "appliance_availability": {},
        "skills_data": {},
    }

    if table and header_row:
        time_slots = _extract_time_slots(header_row)
        crew_result = _extract_crew_availability(date, table, time_slots)
        result["crew_availability"] = crew_result.get("crew_availability", [])

    appliance_availability = parse_appliance_availability(soup, date)
    if appliance_availability:
        result["appliance_availability"] = appliance_availability

    skills_data = parse_skills_table(soup, date)
    if skills_data:
        result["skills_data"] = skills_data

    return result


def parse_station_feed_html(html_content: str) -> Dict[str, Dict[str, Any]]:
    """
    Parses the HTML from the station feed to extract appliance availability.

    Args:
        html_content: The HTML content of the station feed page.

    Returns:
        A dictionary with appliance names as keys and their availability data.
        Example:
        {
            "P22P6": {"availability": True},
        }
    """
    soup = BeautifulSoup(html_content, "lxml")
    availability_data = {}

    # This parsing is based on the specific structure of the ScheduleDisplay.aspx page.
    # It looks for a table with a specific structure to find appliance status.
    table = soup.find("table", {"id": "tblSchedule"})
    if table and isinstance(table, Tag):
        rows = safe_find_all(table, "tr")
        for row in rows:
            cells = safe_find_all(row, "td")
            if len(cells) > 1:
                appliance_name_tag = cells[0].find("span")
                if appliance_name_tag:
                    appliance_name = appliance_name_tag.get_text(strip=True)
                    # The availability is indicated by the background color of the second cell.
                    # Green indicates available, Red indicates unavailable.
                    status_cell = cells[1]
                    style = status_cell.get("style", "")
                    if isinstance(style, str):
                        style = style.lower()
                        if "background-color:green" in style.replace(" ", ""):
                            availability_data[appliance_name] = {"availability": True}
                        elif "background-color:red" in style.replace(" ", ""):
                            availability_data[appliance_name] = {"availability": False}

    return availability_data


def _is_crew_available_in_cell(cell: Optional[Tag]) -> bool:
    """Check if crew member is available based on cell content."""
    if cell is None:
        return False

    # Explicitly check for the 'available' comment code first.
    if cell.get("data-comment") == "1":
        return True

    style = cell.get("style", "")
    cell_text = cell.get_text(strip=True)

    # Check unavailable codes
    if cell_text == "O":  # Off
        return False
    elif cell_text == "W":  # Working
        return False
    elif cell_text == "F":  # Fire call
        return False
    elif cell_text in ["S", "SL", "AL", "H"]:  # Leave types
        return False
    elif cell_text in ["T", "TR", "C"]:  # Training
        return False
    elif isinstance(style, str) and "background-color" in style.lower():
        style_str = style.replace(" ", "").lower()
        # Unavailable colors
        if any(
            color in style_str for color in ["#ff0000", "#ff6666", "#ffcccc", "red"]
        ):
            return False
        elif any(
            color in style_str
            for color in ["#cccccc", "#999999", "#d8dde1", "gray", "grey"]
        ):
            return False

    # If the cell has class 'schTD_off', it's unavailable
    classes = cell.get("class", [])
    if isinstance(classes, list) and "schTD_off" in classes:
        return False

    # If the cell is 'schTD' and doesn't have a specific text code, assume available
    # Our earlier data check showed empty schTD cells are available slots.
    if isinstance(classes, list) and "schTD" in classes and cell_text == "":
        return True

    # Default to not available if no availability indicators are found.
    return False


def _parse_availability_cells(
    avail_cells: List[Tag],
    time_slots: List[str],
    date_prefix: str,
    entity_type: str = "crew",
) -> Dict[str, bool]:
    """Parse availability cells for crew/appliance row."""
    availability = {}
    for i, cell in enumerate(avail_cells):
        slot = time_slots[i]
        slot_key = f"{date_prefix} {slot}"

        is_available = False
        if entity_type == "crew":
            is_available = _is_crew_available_in_cell(cell)
        elif entity_type == "appliance":
            style = cell.get("style", "")
            if isinstance(style, str):
                style_str = style.replace(" ", "").lower()
                if "background-color:#009933" in style_str:
                    is_available = True

        availability[slot_key] = is_available

    return availability
