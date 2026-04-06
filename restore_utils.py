import sys

with open("utils.py", "r") as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if "def get_week_aligned_date_range" in line:
        break
    new_lines.append(line)

# Correct version of get_week_aligned_date_range
new_lines.append(
    "\ndef get_week_aligned_date_range(max_days: int) -> Tuple[datetime, int]:\n"
)
new_lines.append(
    '    """Get start date and effective max days, aligned to current week start."""\n'
)
new_lines.append("    now = get_now()\n")
new_lines.append("    # Start from Monday of current week\n")
new_lines.append(
    "    start_date = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)\n"
)
new_lines.append("    # Adjust max_days to include days from Monday to today\n")
new_lines.append("    effective_max_days = max_days + now.weekday()\n")
new_lines.append("    return start_date, effective_max_days\n")

with open("utils.py", "w") as f:
    f.writelines(new_lines)
