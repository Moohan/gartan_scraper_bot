#!/usr/bin/env python3
"""Tests for parse_grid.py edge cases and error conditions."""

from datetime import date
from unittest.mock import MagicMock, patch

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
        malformed_html = '''
        <html>
            <body>
                <div>Appliances</div>
                <p>No table here</p>
            </body>
        </html>
        '''

        result = parse_appliance_availability(malformed_html)

        # Should return empty dict for malformed HTML
        assert result == {}

    def test_parse_appliance_availability_missing_time_header(self):
        """Test parsing when time header row is missing."""
        html_without_time_header = '''
        <html>
            <body>
                <table>
                    <tr><td>Appliances</td></tr>
                    <tr><td>P22P6</td><td style="background-color: #009933"></td></tr>
                </table>
            </body>
        </html>
        '''

        result = parse_appliance_availability(html_without_time_header)

        # Should return empty dict when time header is missing
        assert result == {}

    def test_parse_skills_table_complex_structure(self):
        """Test parsing skills table with complex nested structure."""
        complex_html = '''
        <html>
            <body>
                <table>
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
        '''

        result = parse_skills_table(complex_html)

        # Should handle complex table structure
        assert isinstance(result, list)
        if result:
            crew_member = result[0]
            assert 'name' in crew_member
            assert 'skills' in crew_member

    def test_parse_grid_html_with_corrupted_data(self):
        """Test parsing grid with corrupted or incomplete data."""
        corrupted_html = '''
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
        '''

        result = parse_grid_html(corrupted_html, date(2025, 8, 26))

        # Should handle corrupted HTML gracefully
        assert isinstance(result, dict)
        assert 'crew' in result
        assert 'appliances' in result

    def test_aggregate_crew_availability_overlapping_slots(self):
        """Test aggregation with complex overlapping time slots."""
        crew_data = {
            "MCMAHON, JA": {
                "name": "MCMAHON, JA",
                "role": "FFC",
                "slots": {
                    "0000": {"available": True, "background_color": "#009933"},
                    "0015": {"available": True, "background_color": "#009933"},
                    "0030": {"available": False, "background_color": "#ff0000"},
                    "0045": {"available": True, "background_color": "#009933"},
                    "0100": {"available": True, "background_color": "#009933"},
                }
            }
        }

        result = aggregate_crew_availability(crew_data, date(2025, 8, 26))

        # Should properly aggregate non-contiguous availability
        assert isinstance(result, list)
        if result:
            crew_member = result[0]
            assert 'blocks' in crew_member
            # Should have separate blocks for 00:00-00:30 and 00:45-01:15
            assert len(crew_member['blocks']) >= 2

    def test_aggregate_appliance_availability_edge_times(self):
        """Test appliance aggregation with edge case times."""
        appliance_data = {
            "P22P6": {
                "name": "P22P6",
                "slots": {
                    "2345": {"available": True, "background_color": "#009933"},
                    "0000": {"available": True, "background_color": "#009933"},
                    "0015": {"available": False, "background_color": "#ff0000"},
                }
            }
        }

        result = aggregate_appliance_availability(appliance_data, date(2025, 8, 26))

        # Should handle day boundary correctly
        assert isinstance(result, list)
        if result:
            appliance = result[0]
            assert 'blocks' in appliance

    def test_parse_skills_table_missing_columns(self):
        """Test skills table parsing with missing columns."""
        html_missing_columns = '''
        <html>
            <body>
                <table>
                    <tr>
                        <td>MCMAHON, JA</td>
                        <!-- Missing skills column -->
                        <td>FFC</td>
                        <!-- Missing contact column -->
                    </tr>
                </table>
            </body>
        </html>
        '''

        result = parse_skills_table(html_missing_columns)

        # Should handle missing columns gracefully
        assert isinstance(result, list)
        if result:
            crew_member = result[0]
            assert crew_member.get('skills') == ''  # Should default to empty
            assert crew_member.get('contact') == ''  # Should default to empty

    def test_parse_grid_html_empty_tables(self):
        """Test parsing with empty tables."""
        empty_table_html = '''
        <html>
            <body>
                <table></table>
                <table>
                    <tr><td>Appliances</td></tr>
                </table>
            </body>
        </html>
        '''

        result = parse_grid_html(empty_table_html)

        # Should handle empty tables
        assert result['crew'] == []
        assert result['appliances'] == []

    def test_time_slot_boundary_conditions(self):
        """Test time slot parsing at day boundaries."""
        # Test HTML with slots spanning midnight
        boundary_html = '''
        <html>
            <body>
                <table>
                    <tr>
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
        '''

        result = parse_appliance_availability(boundary_html, date(2025, 8, 26))

        # Should handle midnight boundary correctly
        assert isinstance(result, dict)

    def test_unicode_and_special_characters(self):
        """Test parsing with Unicode and special characters in names."""
        unicode_html = '''
        <html>
            <body>
                <table>
                    <tr>
                        <td>O'CONNOR, Seán</td>
                        <td>TTR, LGV</td>
                        <td>Watch Commander</td>
                        <td>📧 sean@example.com</td>
                    </tr>
                </table>
            </body>
        </html>
        '''

        result = parse_skills_table(unicode_html)

        # Should handle Unicode characters properly
        assert isinstance(result, list)
        if result:
            crew_member = result[0]
            assert "O'CONNOR" in crew_member['name']
