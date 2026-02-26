import pandas as pd

file_path = "ScottishfrsScottishfrsEmployeeAvailabilityReport.xlsx"
file_path = "ScottishfrsEmployeeAvailabilityReport.xlsx"

try:
    with open("explore_out.txt", "w", encoding="utf-8") as f:
        xl = pd.ExcelFile(file_path)
        f.write(f"Sheets: {xl.sheet_names}\n")
        for sheet in xl.sheet_names:
            df = xl.parse(sheet)
            f.write(f"\nSheet '{sheet}':\n")
            f.write(f"Columns: {df.columns.tolist()}\n")
            f.write("First 15 rows:\n")
            f.write(df.head(15).to_string() + "\n")
except Exception:
    import traceback
    traceback.print_exc()
    raise
