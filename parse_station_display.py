"""
Parses the HTML of the real-time station display page to extract crewing information.
"""

import re
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup, Tag

from utils import log_debug


def parse_station_display_html(html_content: str) -> Optional[Dict[str, Any]]:
    """
    Parses the HTML of the station display page and extracts crewing information.

    Args:
        html_content: The HTML content of the station display page.

    Returns:
        A dictionary containing the parsed information, or None if parsing fails.
    """
    try:
        try:
            soup = BeautifulSoup(html_content, "lxml")
        except Exception:
            # lxml may not be available in some environments (tests/CI), fallback to built-in parser
            log_debug("warn", "lxml parser not available, falling back to html.parser")
            soup = BeautifulSoup(html_content, "html.parser")

        # Extract basic info
        time = soup.find("span", id="lblTime").text.strip()
        date = soup.find("span", id="lblDate").text.strip()
        station = soup.find("span", id="lblStation").text.strip()

        # Extract crewing summary
        crewing_summary_table = soup.find("table", id="gvCrewing")
        crewing_summary = {}
        if crewing_summary_table:
            for row in crewing_summary_table.find_all("tr"):
                cells = row.find_all("td")
                if len(cells) == 2:
                    skill = cells[0].text.strip()
                    values = cells[1].text.strip()
                    match = re.match(r"(\d+)\s*\(([-+]?\d+)\)", values)
                    if match:
                        crewing_summary[skill] = {
                            "available": int(match.group(1)),
                            "difference": int(match.group(2)),
                        }

        # Extract available firefighters
        available_firefighters_table = soup.find("table", id="gvOnDuty")
        available_firefighters = []
        if available_firefighters_table:
            for row in available_firefighters_table.find_all("tr"):
                cells = row.find_all("td")
                if len(cells) == 3:
                    role = cells[0].text.strip()
                    name = cells[1].text.strip()
                    skills = cells[2].text.strip().replace("(", "").replace(")", "")
                    available_firefighters.append(
                        {"role": role, "name": name, "skills": skills.split(", ")}
                    )

        return {
            "time": time,
            "date": date,
            "station": station,
            "crewing_summary": crewing_summary,
            "available_firefighters": available_firefighters,
        }
    except Exception as e:
        log_debug("error", f"An error occurred while parsing station display HTML: {e}")
        return None


if __name__ == "__main__":
    # Example usage with a local HTML file
    try:
        with open("station_display.html", "r", encoding="utf-8") as f:
            html_content = f.read()
        parsed_data = parse_station_display_html(html_content)
        if parsed_data:
            import json

            print("Successfully parsed station display HTML.")
            print(json.dumps(parsed_data, indent=2))
        else:
            print("Failed to parse station display HTML.")
    except FileNotFoundError:
        print("station_display.html not found. Run fetch_station_display.py first.")
    except Exception as e:
        print(f"An error occurred: {e}")
