

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
        return {'crew_availability': []}
    time_slots = _extract_time_slots(header_row)
    return _extract_crew_availability(date, table, time_slots)
def _get_table_and_header(grid_html):
    """
    Extract the main table and header row from the grid HTML.
    Returns (table, header_row) or (None, None) if not found.
    """
    soup = BeautifulSoup(grid_html, 'html.parser')
    table = soup.find('table', attrs={'id': 'gridAvail'})
    if not table:
        return None, None
    from bs4 import Tag
    # Only iterate over direct tr children (Tag elements)
    rows = table.find_all('tr', recursive=False)
    for tr in rows:
        if not isinstance(tr, Tag):
            continue
        tr_class = tr.attrs.get('class', [])
        if isinstance(tr_class, list) and 'gridheader' in tr_class:
            return table, tr
    return table, None

def _extract_time_slots(header_row):
    """
    Extract time slot labels from the header row.
    """
    header_cells = header_row.find_all('td')
    return [cell.get_text(strip=True) for cell in header_cells[5:]]

def _extract_crew_availability(date, table, time_slots):
    """
    Extract crew availability for all rows in the table.
    """
    from datetime import datetime as dt
    date_prefix = _normalize_date(date)
    now = dt.now()
    crew_data = []
    for tr in _extract_crew_rows(table):
        crew_data.append(_parse_crew_row(tr, time_slots, date_prefix, now))
    return {'crew_availability': crew_data}

def _extract_crew_rows(table):
    """
    Return all crew rows (tr) with class 'employee'.
    """
    return [tr for tr in table.find_all('tr') if isinstance(tr.get('class', []), list) and 'employee' in tr.get('class', [])]

def _parse_crew_row(tr, time_slots, date_prefix, now):
    """
    Parse a single crew row and return dict with name, availability, and next_available.
    """
    name = tr.get('data-name', '').strip()
    tds = tr.find_all('td')
    avail_cells = tds[5:]
    availability = _parse_availability_cells(avail_cells, time_slots, date_prefix)
    slot_datetimes = _get_slot_datetimes(avail_cells, time_slots, date_prefix, availability)
    next_avail = _find_next_available(slot_datetimes, now)
    return {'name': name, 'availability': availability, 'next_available': next_avail}

def _parse_availability_cells(avail_cells, time_slots, date_prefix):
    """
    Parse availability cells for a crew row.
    """
    availability = {}
    for i, cell in enumerate(avail_cells):
        val = cell.get_text(strip=True)
        slot = time_slots[i]
        slot_key = f"{date_prefix} {slot}"
        availability[slot_key] = (val == '')
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
    """
    for slot_dt, is_avail in slot_datetimes:
        if slot_dt >= now and is_avail:
            if slot_dt <= now:
                return "now"
            else:
                return slot_dt.strftime("%d/%m/%Y %H:%M")
    return None

def _normalize_date(date):
    """
    Normalize date to dd/mm/yyyy format, or return as-is if not possible.
    """
    from datetime import datetime as dt
    try:
        date_obj = dt.strptime(date, '%d/%m/%Y')
        return date_obj.strftime('%d/%m/%Y')
    except Exception:
        return date or ''
