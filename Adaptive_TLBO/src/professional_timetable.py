"""Professional console rendering for university timetable schedules."""

from __future__ import annotations

import pandas as pd


class ProfessionalTimetable:
    """Displays section-wise university timetables with a lunch break column."""

    LUNCH_COLUMN = "Lunch Break"

    def __init__(self, timetable, days=None, periods=None):
        self.timetable = timetable
        self.days = days or ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        self.periods = periods or [1, 2, 3, 4, 5, 6, 7, 8]

    def section_table(self, section: str) -> pd.DataFrame:
        columns = self._display_columns()
        table = pd.DataFrame("FREE", index=self.days, columns=columns)
        table[self.LUNCH_COLUMN] = "LUNCH BREAK"

        for entry in self.timetable:
            if entry["Section"] != section:
                continue
            day = entry["Day"]
            period = f"P{int(entry['Time'])}"
            table.loc[day, period] = (
                f"{entry['Course']}\n"
                f"{entry['Faculty']}\n"
                f"{entry['Room']}"
            )

        table.index.name = "Day"
        return table

    def display(self):
        sections = sorted({entry["Section"] for entry in self.timetable})
        tables = {}
        print("\n" + "=" * 120)
        print("UNIVERSITY TIMETABLE".center(120))
        print("=" * 120)
        for section in sections:
            table = self.section_table(section)
            tables[section] = table
            print(f"\nSECTION : {section}")
            print("-" * 120)
            print(table.to_string())
        print("=" * 120)
        return tables

    def _display_columns(self):
        columns = []
        for period in self.periods:
            if period == 4:
                columns.append(self.LUNCH_COLUMN)
            columns.append(f"P{period}")
        return columns
