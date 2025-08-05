import pytest
from parse_grid import parse_grid_html

# Example HTML snippet for testing
GRID_HTML = """
<table id="gridAvail">
    <tr class="gridheader">
        <td>Role</td><td>Name</td><td>Skill</td><td>Other</td><td>Other</td><td>0800</td><td>0815</td>
    </tr>
    <tr class="employee">
        <td data-role="Firefighter">John Doe</td><td>John Doe</td><td class="skillCol">Skill</td><td></td><td></td><td data-comment="1"></td><td data-comment="0"></td>
    </tr>
    <tr>
        <td>Engine 1</td><td>Available</td>
    </tr>
</table>
"""


def test_parse_grid_html():
    result = parse_grid_html(GRID_HTML, "2025-07-01")
    assert isinstance(result, dict)
    assert "crew_availability" in result
    assert "appliance_availability" in result
    crew_list = result["crew_availability"]
    assert isinstance(crew_list, list)
    assert crew_list
    crew = crew_list[0]
    assert "name" in crew
    assert "role" in crew
    assert "skills" in crew
    assert "availability" in crew
    slots = crew["availability"]
    assert isinstance(slots, dict)
    # Check slot keys and values
    for k, v in slots.items():
        assert isinstance(v, bool)


import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from gartan_fetch import gartan_login_and_get_session, fetch_and_cache_grid_html
from parse_grid import parse_grid_html


def test_parse_crew_and_appliance():
    """Test that crew and appliance data is parsed correctly from grid HTML."""
    session = gartan_login_and_get_session()
    booking_date = "02/08/2025"
    grid_html = fetch_and_cache_grid_html(session, booking_date)
    result = parse_grid_html(grid_html, booking_date)
    assert "crew_availability" in result
    assert "appliance_availability" in result
    # Check at least one crew and one appliance entry
    assert len(result["crew_availability"]) > 0
    assert len(result["appliance_availability"]) > 0
    # Spot check: crew slots should be boolean
    crew = result["crew_availability"][0]
    assert isinstance(crew["availability"], dict)
    slot_keys = list(crew["availability"].keys())
    assert len(slot_keys) > 0
    assert isinstance(crew["availability"][slot_keys[0]], bool)
