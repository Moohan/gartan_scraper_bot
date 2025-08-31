#!/usr/bin/env python3
"""Enhanced tests for parse_grid.py edge cases and error handling."""

import pytest

from parse_grid import (
    _is_crew_available_in_cell,
    aggregate_appliance_availability,
    aggregate_crew_availability,
    parse_grid_html,
)


class TestParseGridEdgeCases:
    """Test edge cases and error conditions in parse_grid functionality."""

    def test_malformed_html_structures(self):
        """Test parsing with various malformed HTML structures."""

        # Test missing closing tags
        malformed_html1 = """
        <table id='gridAvail'>
          <tr class='gridheader'><td>Name</td><td>0800</td>
          <tr class='employee'><td>John</td><td data-comment='1'></td></tr>
        </table>
        """
        result = parse_grid_html(malformed_html1, "2025-08-05")
        assert isinstance(result, dict)
        assert "crew_availability" in result

        # Test nested table tags
        malformed_html2 = """
        <table id='gridAvail'>
          <table>
            <tr class='gridheader'><td>Name</td><td>0800</td></tr>
            <tr class='employee'><td>Jane</td><td data-comment='0'></td></tr>
          </table>
        </table>
        """
        result = parse_grid_html(malformed_html2, "2025-08-05")
        assert isinstance(result, dict)

        # Test missing table ID
        malformed_html3 = """
        <table>
          <tr class='gridheader'><td>Name</td><td>0800</td></tr>
          <tr class='employee'><td>Bob</td><td data-comment='1'></td></tr>
        </table>
        """
        result = parse_grid_html(malformed_html3, "2025-08-05")
        assert result["crew_availability"] == []  # Should not find table without ID

    def test_unusual_cell_content(self):
        """Test parsing with unusual cell content and attributes."""

        unusual_html = """
        <table id='gridAvail'>
          <tr class='gridheader'><td>Name</td><td>Role</td><td>Skills</td><td>0800</td><td>0815</td></tr>
          <tr class='employee'>
            <td>SPECIAL, CHARS!@#$%</td>
            <td>&lt;Officer&gt;</td>
            <td class='skillCol'>BA&amp;LGV</td>
            <td data-comment='1' style='background-color: red;'></td>
            <td data-comment='F'>Fire Call</td>
          </tr>
        </table>
        """
        result = parse_grid_html(unusual_html, "2025-08-05")
        crew_list = result["crew_availability"]

        assert len(crew_list) == 1
        assert crew_list[0]["name"] == "SPECIAL, CHARS!@#$%"
        assert crew_list[0]["role"] == "<Officer>"  # Should decode HTML entities
        assert "BA&LGV" in crew_list[0]["skills"]

    def test_reason_code_variations(self):
        """Test various reason code formats and edge cases."""

        reason_codes_html = """
        <table id='gridAvail'>
          <tr class='gridheader'><td>Name</td><td>Role</td><td>Contract</td><td>Skills</td><td>0800</td><td>0815</td><td>0830</td><td>0845</td><td>0900</td></tr>
          <tr class='employee'>
            <td>CODES, TEST</td>
            <td>FFC</td>
            <td>61</td>
            <td class='skillCol'>BA</td>
            <td>O</td>
            <td>W</td>
            <td>F</td>
            <td>T</td>
            <td></td>
          </tr>
        </table>
        """
        result = parse_grid_html(reason_codes_html, "2025-08-05")
        crew_list = result["crew_availability"]

        assert len(crew_list) == 1
        availability = crew_list[0]["availability"]

        # O and W should be False (unavailable)
        assert availability["2025-08-05 0800"] is False  # O
        assert availability["2025-08-05 0815"] is False  # W

        # F and T should be False (unavailable)
        assert availability["2025-08-05 0830"] is False  # F
        assert availability["2025-08-05 0845"] is False  # T

        # Empty should be True (available)
        assert availability["2025-08-05 0900"] is True  # Empty

    def test_background_color_parsing(self):
        """Test background color detection for availability."""

        color_html = """
        <table id='gridAvail'>
          <tr class='gridheader'><td>Name</td><td>Role</td><td>Contract</td><td>Skills</td><td>0800</td><td>0815</td><td>0830</td></tr>
          <tr class='employee'>
            <td>COLOR, TEST</td>
            <td>FFC</td>
            <td>61</td>
            <td class='skillCol'>BA</td>
            <td style='background-color: #009933;'></td>
            <td style='background-color: red;'></td>
            <td style='background: green;'></td>
          </tr>
        </table>
        """
        result = parse_grid_html(color_html, "2025-08-05")
        crew_list = result["crew_availability"]

        assert len(crew_list) == 1
        availability = crew_list[0]["availability"]

        # Should have entries for valid time slots that are parsed
        # Red background should indicate unavailable
        assert availability["2025-08-05 0815"] is False  # red (unavailable)
        # Other slots should be available (empty cells with no text)
        assert availability["2025-08-05 0800"] is True  # empty cell with background
        assert availability["2025-08-05 0830"] is True  # empty cell with background

    def test_time_slot_edge_cases(self):
        """Test various time slot formats and edge cases."""

        time_slots_html = """
        <table id='gridAvail'>
          <tr class='gridheader'>
            <td>Name</td>
            <td>2359</td>
            <td>0000</td>
            <td>1200</td>
            <td>Bad Time</td>
            <td></td>
          </tr>
          <tr class='employee'>
            <td>TIME, TEST</td>
            <td></td>
            <td></td>
            <td></td>
            <td></td>
            <td></td>
          </tr>
        </table>
        """
        result = parse_grid_html(time_slots_html, "2025-08-05")
        crew_list = result["crew_availability"]

        assert len(crew_list) == 1
        availability = crew_list[0]["availability"]

        # Valid time slots should be parsed
        assert "2025-08-05 2359" in availability
        assert "2025-08-05 0000" in availability
        # Parser might filter out invalid time formats
        # Let's check what actually gets parsed
        assert len(availability) >= 2  # At least the valid time slots

    def test_crew_role_extraction_edge_cases(self):
        """Test crew role extraction with various formats."""

        role_html = """
        <table id='gridAvail'>
          <tr class='gridheader'><td>Name</td><td>Role</td><td>0800</td></tr>
          <tr class='employee'>
            <td>Name With Role</td>
            <td>Cell Role</td>
            <td></td>
          </tr>
          <tr class='employee'>
            <td>Name Without Role</td>
            <td></td>
            <td></td>
          </tr>
          <tr class='employee'>
            <td>Name With Empty Role</td>
            <td></td>
            <td></td>
          </tr>
        </table>
        """
        result = parse_grid_html(role_html, "2025-08-05")
        crew_list = result["crew_availability"]

        assert len(crew_list) == 3

        # Should extract role from cell content (2nd column)
        crew1 = next(c for c in crew_list if c["name"] == "Name With Role")
        assert crew1["role"] == "Cell Role"

        # Should handle empty role gracefully
        crew2 = next(c for c in crew_list if c["name"] == "Name Without Role")
        assert crew2["role"] == ""

    def test_skills_column_detection(self):
        """Test skills column detection with various configurations."""

        skills_html = """
        <table id='gridAvail'>
          <tr class='gridheader'><td>Name</td><td>Skills</td><td>Other</td><td>0800</td></tr>
          <tr class='employee'>
            <td>SKILLS, TEST</td>
            <td class='skillCol'>BA LGV TTR</td>
            <td>Not Skills</td>
            <td data-comment='1'></td>
          </tr>
          <tr class='employee'>
            <td>NO SKILLS, TEST</td>
            <td class='skillCol'></td>
            <td>Other Data</td>
            <td data-comment='1'></td>
          </tr>
        </table>
        """
        result = parse_grid_html(skills_html, "2025-08-05")
        crew_list = result["crew_availability"]

        assert len(crew_list) == 2

        crew1 = next(c for c in crew_list if c["name"] == "SKILLS, TEST")
        assert crew1["skills"] == "BA LGV TTR"

        crew2 = next(c for c in crew_list if c["name"] == "NO SKILLS, TEST")
        assert crew2["skills"] == ""

    def test_appliance_parsing_edge_cases(self):
        """Test appliance parsing with edge cases."""

        appliance_html = """
        <table id='gridAvail'>
          <tr class='gridheader'><td>Name</td><td>Role</td><td>Contract</td><td>Skills</td><td>0800</td><td>0815</td></tr>
          <tr class='employee'><td>CREW, A</td><td>FFC</td><td>61</td><td class='skillCol'>BA</td><td></td><td>O</td></tr>
          <tr><td colspan="5">Appliances</td></tr>
          <tr><td title="Appliance (0800 - 0815) Available">Appliance</td><td title="P22P6 (0800 - 0815) Available">0800</td><td title="P22P6 (0815 - 0830) Available">0815</td></tr>
          <tr><td colspan="5">P22P6</td><td style='background-color: #009933;'></td><td></td></tr>
          <tr><td colspan="5">ENGINE 1</td><td style='background-color: red;'></td><td style='background-color: #009933;'></td></tr>
        </table>
        """
        result = parse_grid_html(appliance_html, "2025-08-05")
        appliance_data = result["appliance_availability"]

        # Should find P22P6 (current parser only looks for P22P6)
        assert "P22P6" in appliance_data

        # P22P6 should be available at 0800, unavailable at 0815
        p22p6_avail = appliance_data["P22P6"]["availability"]
        assert p22p6_avail["2025-08-05 0800"] is True
        assert p22p6_avail["2025-08-05 0815"] is False

    def test_unicode_and_encoding_edge_cases(self):
        """Test handling of Unicode and special characters."""

        unicode_html = """
        <table id='gridAvail'>
          <tr class='gridheader'><td>Name</td><td>Role</td><td>Skills</td><td>0800</td></tr>
          <tr class='employee'>
            <td>UNICODE, ÑÁMÉ</td>
            <td>Offi©er</td>
            <td class='skillCol'>BÅ LGV</td>
            <td data-comment='1'></td>
          </tr>
          <tr class='employee'>
            <td>EMOJI, 🚒</td>
            <td>👨‍🚒</td>
            <td class='skillCol'>💨🚗</td>
            <td data-comment='0'></td>
          </tr>
        </table>
        """
        result = parse_grid_html(unicode_html, "2025-08-05")
        crew_list = result["crew_availability"]

        assert len(crew_list) == 2

        # Should handle Unicode characters correctly
        crew1 = next(c for c in crew_list if "UNICODE" in c["name"])
        assert "ÑÁMÉ" in crew1["name"]
        assert "Offi©er" in crew1["role"]
        assert "BÅ" in crew1["skills"]

        # Should handle emoji (though may not be realistic)
        crew2 = next(c for c in crew_list if "EMOJI" in c["name"])
        assert "🚒" in crew2["name"]

    def test_large_grid_performance(self):
        """Test parsing performance with larger grids."""

        # Generate a larger HTML grid
        header = "<table id='gridAvail'><tr class='gridheader'><td>Name</td><td>Role</td><td>Skills</td>"
        for hour in range(24):
            for minute in [0, 15, 30, 45]:
                time_str = f"{hour:02d}{minute:02d}"
                header += f"<td>{time_str}</td>"
        header += "</tr>"

        crew_rows = ""
        for i in range(50):  # 50 crew members
            crew_rows += f"<tr class='employee'><td>CREW, {i:02d}</td><td>FFC</td><td class='skillCol'>BA</td>"
            for hour in range(24):
                for minute in [0, 15, 30, 45]:
                    available = "1" if (i + hour + minute) % 3 == 0 else "0"
                    crew_rows += f"<td data-comment='{available}'></td>"
            crew_rows += "</tr>"

        large_html = header + crew_rows + "</table>"

        # Should complete without timeout or excessive memory usage
        result = parse_grid_html(large_html, "2025-08-05")
        assert len(result["crew_availability"]) == 50

        # Spot check a few crew members
        crew_0 = next(c for c in result["crew_availability"] if c["name"] == "CREW, 00")
        assert len(crew_0["availability"]) == 96  # 24 hours * 4 slots per hour

    def test_is_crew_available_in_cell_edge_cases(self):
        """Test the _is_crew_available_in_cell function directly."""

        # Test with None cell
        assert _is_crew_available_in_cell(None) is False

        # Test with mock cell that has no attributes
        class MockCell:
            def get(self, attr, default=None):
                return default

            def get_text(self, strip=True):
                return ""

        empty_cell = MockCell()
        assert _is_crew_available_in_cell(empty_cell) is True  # No content = available

        # Test with reason codes
        class MockCellWithText:
            def __init__(self, text):
                self.text = text

            def get(self, attr, default=None):
                return default

            def get_text(self, strip=True):
                return self.text

        # Test all reason codes
        assert _is_crew_available_in_cell(MockCellWithText("O")) is False  # Off
        assert _is_crew_available_in_cell(MockCellWithText("W")) is False  # Working
        assert _is_crew_available_in_cell(MockCellWithText("T")) is False  # Training
        assert (
            _is_crew_available_in_cell(MockCellWithText("")) is True
        )  # Empty = available

    def test_aggregation_with_conflicting_data(self):
        """Test aggregation functions with conflicting data."""

        # Test crew aggregation with conflicts
        conflicting_crew = [
            [
                {
                    "name": "CONFLICT, A",
                    "role": "FFC",
                    "availability": {"2025-08-05 0800": True},
                }
            ],
            [
                {
                    "name": "CONFLICT, A",
                    "role": "FFT",
                    "availability": {"2025-08-05 0800": False},
                }
            ],
        ]

        aggregated = aggregate_crew_availability(conflicting_crew)
        assert len(aggregated) == 1  # Should merge into one entry

        # Should handle the conflict gracefully (last one wins or merged)
        conflict_crew = aggregated[0]
        assert conflict_crew["name"] == "CONFLICT, A"

        # Test appliance aggregation with conflicts
        conflicting_appliances = [
            {"ENGINE": {"availability": {"2025-08-05 0800": True}}},
            {"ENGINE": {"availability": {"2025-08-05 0800": False}}},
        ]

        aggregated_appliances = aggregate_appliance_availability(conflicting_appliances)
        # Should handle gracefully without crashing


class TestParseSkillsTable:
    """Test the parse_skills_table function which was not covered."""

    def test_parse_skills_table_complete(self):
        """Test parse_skills_table with complete skills data."""
        from parse_grid import parse_skills_table

        html = """
        <table>
            <tr><td>Rules</td></tr>
            <tr><td>Time</td><td>0800</td><td>0815</td><td>0830</td></tr>
            <tr><td>BA</td><td>4</td><td>3</td><td>5</td></tr>
            <tr><td>LGV</td><td>2</td><td>1</td><td>2</td></tr>
            <tr><td>Total Crew</td><td>8</td><td>6</td><td>9</td></tr>
            <tr><td>MGR</td><td>1</td><td>1</td><td>1</td></tr>
        </table>
        """
        result = parse_skills_table(html, "2025-08-05")

        assert "skills_availability" in result
        skills = result["skills_availability"]

        # Check all skill types are parsed
        assert "BA" in skills
        assert "LGV" in skills
        assert "Total Crew" in skills
        assert "MGR" in skills

        # Check specific values
        assert skills["BA"]["2025-08-05 0800"] == 4
        assert skills["LGV"]["2025-08-05 0815"] == 1
        assert skills["Total Crew"]["2025-08-05 0830"] == 9

    def test_parse_skills_table_no_table(self):
        """Test parse_skills_table with no Rules table."""
        from parse_grid import parse_skills_table

        html = """
        <table>
            <tr><td>Not Rules</td></tr>
            <tr><td>Other Data</td></tr>
        </table>
        """
        result = parse_skills_table(html, "2025-08-05")
        assert result == {}

    def test_parse_skills_table_no_header_row(self):
        """Test parse_skills_table with Rules but no header row after."""
        from parse_grid import parse_skills_table

        html = """
        <table>
            <tr><td>Rules</td></tr>
        </table>
        """
        result = parse_skills_table(html, "2025-08-05")
        assert result == {}

    def test_parse_skills_table_invalid_data(self):
        """Test parse_skills_table with invalid numeric data."""
        from parse_grid import parse_skills_table

        html = """
        <table>
            <tr><td>Rules</td></tr>
            <tr><td>Time</td><td>0800</td><td>0815</td></tr>
            <tr><td>BA</td><td>invalid</td><td></td></tr>
            <tr><td>LGV</td><td>abc</td><td>3.5</td></tr>
        </table>
        """
        result = parse_skills_table(html, "2025-08-05")
        skills = result["skills_availability"]

        # Should handle invalid data gracefully
        assert skills["BA"]["2025-08-05 0800"] == 0
        assert skills["BA"]["2025-08-05 0815"] == 0  # Empty string
        assert skills["LGV"]["2025-08-05 0800"] == 0  # Non-numeric


class TestMissingLineCoverage:
    """Test specific missing lines to improve coverage."""

    def test_get_table_and_header_no_gridavail(self):
        """Test _get_table_and_header when no gridAvail table exists (line 144)."""
        from parse_grid import _get_table_and_header

        html = (
            "<html><body><table id='other'><tr><td>test</td></tr></table></body></html>"
        )
        table, header = _get_table_and_header(html)
        assert table is None
        assert header is None

    def test_appliance_parsing_edge_cases(self):
        """Test appliance parsing edge cases (lines 318-319, 330, 336, 351-353)."""
        from parse_grid import parse_appliance_availability

        # Test no time header row after "Appliances"
        html1 = """
        <table id='gridAvail'>
            <tr><td colspan='5'>Appliances</td></tr>
            <tr><td>P22P6</td><td>Available</td></tr>
        </table>
        """
        result1 = parse_appliance_availability(html1, "2025-08-05")
        # Should handle gracefully, might return data or empty dict
        assert isinstance(result1, dict)  # Should not crash

        # Test empty title attribute
        html2 = """
        <table id='gridAvail'>
            <tr><td colspan='5'>Appliances</td></tr>
            <tr><td>Time</td><td title="">0800</td><td>0815</td></tr>
            <tr><td colspan='5'>P22P6</td><td style='background-color: #009933'></td><td></td></tr>
        </table>
        """
        result2 = parse_appliance_availability(html2, "2025-08-05")
        assert "P22P6" in result2  # Line 336

        # Test no P22P6 row found
        html3 = """
        <table id='gridAvail'>
            <tr><td colspan='5'>Appliances</td></tr>
            <tr><td>Time</td><td title="P22P6 (0800 - 0815) Available">0800</td></tr>
            <tr><td colspan='5'>Engine1</td><td></td></tr>
        </table>
        """
        result3 = parse_appliance_availability(html3, "2025-08-05")
        # Should set all slots to False when P22P6 row not found (lines 351-353)
        appliance_data = list(result3.values())[0]
        assert not appliance_data["availability"]["2025-08-05 0800"]

    def test_unknown_appliance_name_fallback(self):
        """Test unknown appliance name fallback (line 388)."""
        from parse_grid import parse_appliance_availability

        html = """
        <table id='gridAvail'>
            <tr><td colspan='5'>Appliances</td></tr>
            <tr><td>Time</td><td title="P22P6 (0800 - 0815) Available">0800</td></tr>
            <tr><td colspan='5'></td><td style='background-color: #009933'></td></tr>
        </table>
        """
        result = parse_appliance_availability(html, "2025-08-05")
        # Should use "UNKNOWN" when appliance name not found
        assert "UNKNOWN" in result

    def test_normalize_date_edge_cases(self):
        """Test _normalize_date with various formats."""
        from parse_grid import _normalize_date

        # Test various date formats
        assert _normalize_date("05-08-2025") == "05-08-2025"  # Returns as-is
        assert _normalize_date("2025-08-05") == "2025-08-05"  # Returns as-is
        assert _normalize_date("05/08/2025") == "05/08/2025"  # Returns as-is

        # Test invalid format - should return as-is
        assert _normalize_date("invalid-date") == "invalid-date"
        assert _normalize_date("") == ""

    def test_aggregate_crew_availability_edge_cases(self):
        """Test aggregate_crew_availability edge cases (lines 493, 512)."""
        from parse_grid import aggregate_crew_availability

        # Test with complex availability patterns to trigger edge case logic
        daily_crew_lists = [
            [
                {
                    "name": "EDGE, CASE",
                    "role": "FFC",
                    "skills": "BA",
                    "availability": {
                        "2025-08-05 0800": True,
                        "2025-08-05 0815": False,
                        "2025-08-05 0830": True,
                        "2025-08-05 0845": True,
                        "2025-08-05 0900": False,
                    },
                }
            ]
        ]

        result = aggregate_crew_availability(daily_crew_lists)
        assert len(result) == 1

        crew = result[0]
        # Should calculate next_available and other status fields
        assert "next_available" in crew
        assert "next_available_until" in crew
        assert "available_now" in crew


if __name__ == "__main__":
    pytest.main([__file__])
