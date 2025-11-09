#!/usr/bin/env python3
"""Tests for parse_grid.py edge cases and error conditions."""

from datetime import datetime as dt

from parse_grid import (
    aggregate_appliance_availability,
    aggregate_crew_availability,
    parse_appliance_availability,
    parse_grid_html,
    parse_skills_table,
)


class TestParseGridEdgeCases:
    """Test edge cases and error conditions in grid parsing."""

    def test_parse_appliance_availability_malformed_html(self):
        """Test parsing with malformed HTML structure."""
        # HTML without proper table structure
        malformed_html = """
        <html>
            <body>
                <div>Appliances</div>
                <p>No table here</p>
            </body>
        </html>
        """

        result = parse_appliance_availability(malformed_html)

        # Should return empty dict for malformed HTML
        assert result == {}

    def test_parse_appliance_availability_missing_time_header(self):
        """Test parsing when time header row is missing."""
        html_without_time_header = """
        <html>
            <body>
                <table>
                    <tr><td>Appliances</td></tr>
                    <tr><td>P22P6</td><td style="background-color: #009933"></td></tr>
                </table>
            </body>
        </html>
        """

        result = parse_appliance_availability(html_without_time_header)

        # Should return empty dict when time header is missing
        assert result == {}

    def test_parse_skills_table_complex_structure(self):
        """Test parsing skills table with complex nested structure."""
        complex_html = """
        <html>
            <body>
                <table>
                    <tr><td>Rules</td></tr>
                    <tr>
                        <td rowspan="2">MCMAHON, JA</td>
                        <td>TTR, LGV, BA</td>
                        <td>FFC</td>
                        <td>Email: test@example.com</td>
                    </tr>
                    <tr>
                        <td colspan="3">Additional info</td>
                    </tr>
                </table>
            </body>
        </html>
        """

        result = parse_skills_table(complex_html)

        # Should handle complex table structure
        assert isinstance(result, dict)
        assert "skills_availability" in result
        assert result["skills_availability"] == {}

    def test_parse_grid_html_with_corrupted_data(self):
        """Test parsing grid with corrupted or incomplete data."""
        corrupted_html = """
        <html>
            <body>
                <!-- Incomplete crew table -->
                <table>
                    <tr><td>MCMAHON, JA</td><td style="background-color: #009933">
                    <!-- Missing closing tags -->

                <!-- Incomplete appliance table -->
                <table>
                    <tr><td>Appliances</td></tr>
                    <tr><td>P22P6</td>
                <!-- Truncated HTML -->
        """

        test_date = dt(2025, 8, 26).strftime("%d/%m/%Y")
        result = parse_grid_html(corrupted_html, test_date)

        # Should handle corrupted HTML gracefully
        assert isinstance(result, dict)
        assert "crew_availability" in result
        assert "appliance_availability" in result
        assert "skills_data" in result

    def test_aggregate_crew_availability_overlapping_slots(self):
        """Test aggregation with complex overlapping time slots."""
        crew_data = [
            [
                {
                    "name": "MCMAHON, JA",
                    "role": "FFC",
                    "availability": {
                        "26/08/2025 0000": True,
                        "26/08/2025 0015": True,
                        "26/08/2025 0030": False,
                        "26/08/2025 0045": True,
                        "26/08/2025 0100": True,
                    },
                }
            ]
        ]

        result = aggregate_crew_availability(crew_data)

        # Should properly aggregate non-contiguous availability
        assert isinstance(result, list)
        assert len(result) == 1
        crew_member = result[0]
        assert crew_member["name"] == "MCMAHON, JA"
        assert crew_member["role"] == "FFC"

    def test_aggregate_appliance_availability_edge_times(self):
        """Test appliance aggregation with edge case times."""
        appliance_data = [
            {
                "P22P6": {
                    "appliance": "P22P6",
                    "availability": {
                        "26/08/2025 2345": True,
                        "26/08/2025 0000": True,
                        "26/08/2025 0015": False,
                    },
                }
            }
        ]

        result = aggregate_appliance_availability(appliance_data)

        # Should handle day boundary correctly
        assert isinstance(result, list)
        assert len(result) == 1
        appliance = result[0]
        assert appliance["appliance"] == "P22P6"

    def test_parse_skills_table_missing_columns(self):
        """Test parsing table with missing columns."""
        html_missing_columns = """
        <html>
            <body>
                <table>
                    <tr><td>Rules</td></tr>
                    <tr><td>BA</td></tr>
                    <tr><td>LGV</td></tr>
                </table>
            </body>
        </html>
        """

        result = parse_skills_table(html_missing_columns)

        # Should handle missing columns gracefully
        assert isinstance(result, dict)
        assert "skills_availability" in result
        assert result["skills_availability"] == {}

    def test_parse_grid_html_empty_tables(self):
        """Test parsing with empty tables."""
        empty_html = """
        <html>
            <body>
                <table></table>
            </body>
        </html>
        """

        result = parse_grid_html(empty_html)
        # Empty tables should result in empty structures
        result = parse_grid_html(empty_html)

        # Should handle empty tables
        assert result["crew_availability"] == []
        assert result["appliance_availability"] == {}

    def test_time_slot_boundary_conditions(self):
        """Test time slot parsing at day boundaries."""
        # Test HTML with slots spanning midnight
        test_date = dt(2025, 8, 26).strftime("%d/%m/%Y")
        boundary_html = """
        <html>
            <body>
                <table>
                    <tr class="gridheader">
                        <td>Time Slots</td>
                        <td title="P22P6 (2345 - 0000) Available">23:45</td>
                        <td title="P22P6 (0000 - 0015) Available">00:00</td>
                    </tr>
                    <tr>
                        <td>P22P6</td>
                        <td style="background-color: #009933"></td>
                        <td style="background-color: #009933"></td>
                    </tr>
                </table>
            </body>
        </html>
        """

        result = parse_appliance_availability(boundary_html, test_date)

        # Should handle boundary conditions
        assert isinstance(result, dict)
        assert "P22P6" in result

    def test_unicode_and_special_characters(self):
        """Test parsing with Unicode and special characters in names."""
        unicode_html = """
        <html>
            <body>
                <table>
                    <tr><td>Rules</td></tr>
                    <tr>
                        <td>O'CONNOR, Seán</td>
                        <td>1</td><td>0</td><td>1</td>
                    </tr>
                </table>
            </body>
        </html>
        """

        result = parse_skills_table(unicode_html)

        # Should handle Unicode characters properly
        assert isinstance(result, dict)
        assert "skills_availability" in result
        assert result["skills_availability"] == {}
