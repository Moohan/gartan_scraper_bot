

# parse_grid.py: provides parse_grid_html(grid_html, date=None)
from bs4 import BeautifulSoup
import json

def parse_grid_html(grid_html, date=None):
    """
    Parse the grid HTML and return structured crew availability data.
    Args:
        grid_html (str): HTML string of the gridAvail table
        date (str): booking date (optional)
    Returns:
        dict: { 'date': date, 'crew': [ { 'name': ..., 'availability': { time: bool, ... } }, ... ] }
    """
    soup = BeautifulSoup(grid_html, 'html.parser')
    table = soup.find('table', {'id': 'gridAvail'})
    if not table:
        return {'crew_availability': []}
    header_row = table.find('tr', class_='gridheader')
    if not header_row:
        return {'crew_availability': []}
    header_cells = header_row.find_all('td')
    time_slots = [cell.get_text(strip=True) for cell in header_cells[5:]]

    return extract_crew_availability(date, table, time_slots)


def extract_crew_availability(date, table, time_slots):
    from datetime import datetime
    # Normalize date to dd/mm/yyyy
    try:
        date_obj = datetime.strptime(date, '%d/%m/%Y')
        date_prefix = date_obj.strftime('%d/%m/%Y')
    except Exception:
        date_prefix = date or ''

    from datetime import datetime as dt
    now = dt.now()
    crew_data = []
    for tr in table.find_all('tr'):
        tr_class = tr.get('class', [])
        if isinstance(tr_class, list) and 'employee' in tr_class:
            name = tr.get('data-name', '').strip()
            tds = tr.find_all('td')
            avail_cells = tds[5:]
            availability = {}
            slot_datetimes = []
            for i, cell in enumerate(avail_cells):
                val = cell.get_text(strip=True)
                slot = time_slots[i]
                slot_key = f"{date_prefix} {slot}"
                availability[slot_key] = (val == '')
                # Parse slot datetime for next_available calculation
                try:
                    slot_dt = dt.strptime(f"{date_prefix} {slot}", "%d/%m/%Y %H%M")
                    slot_datetimes.append((slot_dt, availability[slot_key]))
                except Exception:
                    pass
            # Find next available time
            next_avail = None
            for slot_dt, is_avail in slot_datetimes:
                if slot_dt >= now and is_avail:
                    if slot_dt <= now:
                        next_avail = "now"
                    else:
                        next_avail = slot_dt.strftime("%d/%m/%Y %H:%M")
                    break
            crew_data.append({'name': name, 'availability': availability, 'next_available': next_avail})

    result = {
        'crew_availability': crew_data
    }
    return result
