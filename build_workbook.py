#!/usr/bin/env python3
"""
Build a single .xlsx workbook with one tab per domain from the CSVs produced by
keyword_research.py. Uploading this to Google Drive with conversion enabled
yields one Google Sheet with two tabs.
"""
import csv
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment
from openpyxl.utils import get_column_letter

DATA_DIR = Path(__file__).parent / "data"
OUT_PATH = Path(__file__).parent / "Keyword Research.xlsx"

# (csv filename, tab name)
TABS = [
    ("sundaycitizen_co.csv",     "sundaycitizen.co"),
    ("brooklinen_com.csv",       "brooklinen.com"),
    ("brooklinen_expansion.csv", "brooklinen — expansion"),
    ("serp_competitors.csv",     "competing domains"),
]

# numeric columns -> formatting
NUM_COLS = {"search_volume", "etv", "position", "keyword_difficulty", "cpc",
            "keywords_in_space", "etv_in_space", "traffic_share_pct",
            "avg_position", "visibility"}
INT_COLS = {"search_volume", "position", "keyword_difficulty",
            "keywords_in_space", "etv_in_space"}


def add_sheet(wb, csv_name, tab_name, first):
    ws = wb.active if first else wb.create_sheet()
    ws.title = tab_name

    with (DATA_DIR / csv_name).open() as f:
        reader = csv.reader(f)
        header = next(reader)
        ws.append(header)
        col_idx = {name: i for i, name in enumerate(header)}
        for row in reader:
            out = []
            for i, val in enumerate(row):
                name = header[i]
                if name in NUM_COLS and val not in ("", None):
                    try:
                        num = float(val)
                        out.append(int(round(num)) if name in INT_COLS else round(num, 2))
                        continue
                    except ValueError:
                        pass
                out.append(val)
            ws.append(out)

    # header styling
    bold = Font(bold=True)
    for cell in ws[1]:
        cell.font = bold
        cell.alignment = Alignment(horizontal="left")
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions

    # column widths
    widths = {
        "keyword": 38, "search_volume": 14, "etv": 12, "position": 10,
        "ranking_url": 60, "keyword_difficulty": 18, "cpc": 8, "search_intent": 15,
        "competition": 13, "source": 16,
        "domain": 32, "category": 14, "keywords_in_space": 17,
        "etv_in_space": 14, "traffic_share_pct": 16, "avg_position": 12,
        "visibility": 12,
    }
    for name, idx in col_idx.items():
        ws.column_dimensions[get_column_letter(idx + 1)].width = widths.get(name, 14)

    print(f"  {tab_name}: {ws.max_row - 1} rows")


def main():
    wb = Workbook()
    for i, (csv_name, tab_name) in enumerate(TABS):
        add_sheet(wb, csv_name, tab_name, first=(i == 0))
    wb.save(OUT_PATH)
    print(f"wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
