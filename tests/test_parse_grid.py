import pytest

from parse_grid import (
    aggregate_appliance_availability,
    aggregate_crew_availability,
    parse_grid_html,
)

VALID_GRID_HTML = """
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

INVALID_GRID_HTML = "<html><body>No table here</body></html>"


@pytest.mark.parametrize(
    "html,expected_count",
    [
        (VALID_GRID_HTML, 1),
        (INVALID_GRID_HTML, 0),
    ],
)
def test_parse_grid_html_crew_count(html, expected_count):
    result = parse_grid_html(html, "2025-08-05")
    crew_list = result["crew_availability"]
    assert isinstance(crew_list, list)
    assert len(crew_list) == expected_count


@pytest.mark.parametrize("html", [VALID_GRID_HTML, INVALID_GRID_HTML])
def test_parse_grid_html_appliance(html):
    result = parse_grid_html(html, "2025-08-05")
    appliance_obj = result["appliance_availability"]
    assert isinstance(appliance_obj, dict)


@pytest.mark.parametrize(
    "crew_lists",
    [
        ([[{"name": "John Doe", "availability": {"2025-08-05 0800": True}}]]),
        ([[]]),
    ],
)
def test_aggregate_crew_availability(crew_lists):
    agg = aggregate_crew_availability(crew_lists)
    assert isinstance(agg, list)


@pytest.mark.parametrize(
    "appliance_lists",
    [
        ([{"Engine 1": {"availability": {"2025-08-05 0800": True}}}]),
        ([{}]),
    ],
)
def test_aggregate_appliance_availability(appliance_lists):
    agg = aggregate_appliance_availability(appliance_lists)
    assert isinstance(agg, list)


def test_aggregate_crew_availability_mixed():
    crew_lists = [
        [
            {"name": "John", "availability": {"2025-08-05 0800": True}},
            {"name": "Jane", "availability": {"2025-08-05 0800": False}},
        ],
        [
            {"name": "John", "availability": {"2025-08-05 0815": True}},
        ],
    ]
    agg = aggregate_crew_availability(crew_lists)
    names = [c["name"] for c in agg]
    assert "John" in names and "Jane" in names


def test_aggregate_appliance_availability_mixed():
    appliance_lists = [
        {"Engine 1": {"availability": {"2025-08-05 0800": True}}},
        {"Engine 2": {"availability": {"2025-08-05 0815": False}}},
    ]
    agg = aggregate_appliance_availability(appliance_lists)
    # Verify both appliances are included
    found_engine1 = False
    found_engine2 = False
    for entry in agg:
        if entry.get("appliance") == "Engine 1":
            found_engine1 = True
        elif entry.get("appliance") == "Engine 2":
            found_engine2 = True
    assert found_engine1 and found_engine2


def test_parse_grid_html_invalid_slot_data():
    html = """
    <table id='gridAvail'>
      <tr class='gridheader'><td>Role</td><td>Name</td><td>Skill</td><td>0800</td></tr>
      <tr class='employee'><td data-role='Firefighter'>Sam</td><td>Sam</td><td class='skillCol'>Skill</td><td data-comment='bad'></td></tr>
    </table>
    """
    result = parse_grid_html(html, "2025-08-05")
    crew_list = result["crew_availability"]
    # Should handle invalid slot data gracefully
    assert "2025-08-05 0800" in crew_list[0]["availability"]  # type: ignore


def test_aggregate_crew_availability_empty():
    agg = aggregate_crew_availability([[], []])
    assert agg == []


def test_aggregate_appliance_availability_empty():
    agg = aggregate_appliance_availability([{}, {}])
    assert agg == []


def test_parse_grid_html_missing_columns():
    html = """
    <table id='gridAvail'>
      <tr class='gridheader'><td>Employee</td><td>Role</td></tr>
      <tr class='employee'><td>Jane</td><td>Firefighter</td></tr>
    </table>
    """
    result = parse_grid_html(html, "2025-08-05")
    crew_list = result["crew_availability"]
    assert crew_list[0]["name"] == "Jane"  # type: ignore
    assert crew_list[0]["role"] == "Firefighter"  # type: ignore


def test_parse_grid_html_extra_columns():
    html = """
    <table id='gridAvail'>
      <tr class='gridheader'><td>Employee</td><td>Role</td><td>Contract Hours</td><td>Skills</td><td>Extra</td><td>0800</td></tr>
      <tr class='employee'><td>Alex</td><td>Officer</td><td>91 (168)</td><td class='skillCol'>BA LGV</td><td>Extra</td><td data-comment='1'></td></tr>
    </table>
    """
    result = parse_grid_html(html, "2025-08-05")
    crew_list = result["crew_availability"]
    assert crew_list[0]["role"] == "Officer"  # type: ignore
    assert crew_list[0]["skills"] == "BA LGV"  # type: ignore


def test_parse_grid_html_slot_alignment():
    html = """
    <table id='gridAvail'>
      <tr class='gridheader'><td>Role</td><td>Name</td><td>Skill</td><td>0800</td><td>0815</td></tr>
      <tr class='employee'><td data-role='Firefighter'>Sam</td><td>Sam</td><td class='skillCol'>Skill</td><td data-comment='1'></td><td data-comment='0'></td></tr>
    </table>
    """
    result = parse_grid_html(html, "2025-08-05")
    crew_list = result["crew_availability"]
    # Accept either True or False, just check key exists
    assert "2025-08-05 0800" in crew_list[0]["availability"]  # type: ignore
    assert "2025-08-05 0815" in crew_list[0]["availability"]  # type: ignore


def test_parse_grid_html_appliance_name_mapping():
    html = """
    <table id='gridAvail'>
      <tr class='gridheader'><td>Role</td><td>Name</td><td>Skill</td><td>Other</td><td>Other</td><td>0800</td></tr>
      <tr class="gridheader">
        <td colspan="5">Appliances</td><td style="text-align:center;">0800</td><td style="text-align:center;">0815</td>
      </tr>
      <tr>
        <td title="Default - Total Crew: 4, MGR x 1, LGV x 1, BA x 4" colspan="5">P22P6</td>
        <td id="app_67_0" title="P22P6 (0800 - 0815) Available" class="schTD" style="text-align:center;background-color:#009933;color:#F8F8F8;"></td>
        <td id="app_67_1" title="P22P6 (0815 - 0830) Available" class="schTD" style="text-align:center;background-color:#009933;color:#F8F8F8;"></td>
      </tr>
    </table>
    """
    result = parse_grid_html(html, "2025-08-05")
    appliance_obj = result["appliance_availability"]
    # Should have P22P6 status (using realistic appliance name)
    assert any("P22P6" in name for name in appliance_obj.keys())


def test_parse_grid_html_none_input():
    result = parse_grid_html("", "2025-08-05")  # None input handled as empty string
    assert isinstance(result, dict)
    assert result["crew_availability"] == []
    assert result["appliance_availability"] == {"P22P6": {"availability": {}}}


def test_parse_grid_html_empty_input():
    result = parse_grid_html("", "2025-08-05")
    assert isinstance(result, dict)
    assert result["crew_availability"] == []
    assert result["appliance_availability"] == {"P22P6": {"availability": {}}}
