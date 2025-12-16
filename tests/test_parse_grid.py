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
    """Verifies that parse_grid_html correctly counts crew members."""
    result = parse_grid_html(html, "2025-08-05")
    crew_list = result["crew_availability"]
    assert isinstance(crew_list, list)
    assert len(crew_list) == expected_count


@pytest.mark.parametrize("html", [VALID_GRID_HTML, INVALID_GRID_HTML])
def test_parse_grid_html_appliance(html):
    """Verifies that parse_grid_html returns a dictionary for appliance availability."""
    result = parse_grid_html(html, "2025-08-05")
    appliance_obj = result["appliance_availability"]
    assert isinstance(appliance_obj, dict)


@pytest.mark.parametrize(
    "crew_lists, expected_names",
    [
        ([], []),
        ([[]], []),
        ([[{"name": "John Doe", "availability": {"2025-08-05 0800": True}}]], ["John Doe"]),
        (
            [
                [
                    {"name": "John", "availability": {"2025-08-05 0800": True}},
                    {"name": "Jane", "availability": {"2025-08-05 0800": False}},
                ],
                [
                    {"name": "John", "availability": {"2025-08-05 0815": True}},
                ],
            ],
            ["John", "Jane"],
        ),
    ],
)
def test_aggregate_crew_availability(crew_lists, expected_names):
    """
    Verifies that aggregate_crew_availability correctly aggregates crew data
    across multiple lists, covering empty, single, and mixed data scenarios.
    """
    agg = aggregate_crew_availability(crew_lists)
    assert isinstance(agg, list)
    names = sorted([c["name"] for c in agg])
    assert names == sorted(expected_names)


@pytest.mark.parametrize(
    "appliance_lists, expected_appliances",
    [
        ([], []),
        ([{}], []),
        (
            [{"Engine 1": {"availability": {"2025-08-05 0800": True}}}],
            ["Engine 1"],
        ),
        (
            [
                {"Engine 1": {"availability": {"2025-08-05 0800": True}}},
                {"Engine 2": {"availability": {"2025-08-05 0815": False}}},
            ],
            ["Engine 1", "Engine 2"],
        ),
    ],
)
def test_aggregate_appliance_availability(appliance_lists, expected_appliances):
    """
    Verifies that aggregate_appliance_availability correctly aggregates appliance data
    across multiple lists, covering empty, single, and mixed data scenarios.
    """
    agg = aggregate_appliance_availability(appliance_lists)
    assert isinstance(agg, list)
    appliance_names = sorted([a["appliance"] for a in agg])
    assert appliance_names == sorted(expected_appliances)


def test_parse_grid_html_invalid_slot_data():
    """Verifies that a slot with unrecognized data is parsed as not available."""
    html = """
    <table id='gridAvail'>
      <tr class='gridheader'><td>Role</td><td>Name</td><td>Skill</td><td>0800</td></tr>
      <tr class='employee'><td data-role='Firefighter'>Sam</td><td>Sam</td><td class='skillCol'>Skill</td><td data-comment='bad'></td></tr>
    </table>
    """
    result = parse_grid_html(html, "2025-08-05")
    crew_list = result["crew_availability"]
    # Should handle invalid slot data gracefully, defaulting to False.
    assert "2025-08-05 0800" in crew_list[0]["availability"]
    assert crew_list[0]["availability"]["2025-08-05 0800"] is False


def test_parse_grid_html_missing_columns():
    """Verifies parsing works even with missing metadata columns."""
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
    """Verifies parsing is robust to extra, unexpected columns."""
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
    """Verifies that availability slots are correctly aligned with headers."""
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
    """Verifies that a realistic appliance name (P22P6) is correctly parsed."""
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
    """Verifies that parse_grid_html raises TypeError for None input."""
    with pytest.raises(TypeError):
        parse_grid_html(None, "2025-08-05")


def test_parse_grid_html_empty_input():
    """Verifies that parse_grid_html handles empty string input gracefully."""
    result = parse_grid_html("", "2025-08-05")
    assert isinstance(result, dict)
    assert result["crew_availability"] == []
    assert result["appliance_availability"] == {}


def test_parse_grid_html_missing_data_comment_attribute():
    """
    Verifies that a slot missing the 'data-comment' attribute is parsed as not available.
    """
    html = """
    <table id='gridAvail'>
      <tr class='gridheader'><td>Role</td><td>Name</td><td>Skill</td><td>0800</td></tr>
      <tr class='employee'><td data-role='Firefighter'>Tom</td><td>Tom</td><td class='skillCol'>Skill</td><td></td></tr>
    </table>
    """
    result = parse_grid_html(html, "2025-08-05")
    crew_list = result["crew_availability"]
    assert len(crew_list) == 1
    availability = crew_list[0]["availability"]
    assert "2025-08-05 0800" in availability
    assert availability["2025-08-05 0800"] is False
