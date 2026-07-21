"""Constraint checks for academic timetable schedules."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Dict, Iterable, Tuple


class ConstraintChecker:
    """Computes hard and soft constraint violations."""

    def _count_duplicate_keys(self, keys: Iterable[Tuple[object, ...]]) -> int:
        counter = Counter(keys)
        return sum(count - 1 for count in counter.values() if count > 1)

    def section_conflicts(self, timetable) -> int:
        return self._count_duplicate_keys(
            (entry["Section"], entry["Day"], int(entry["Time"]))
            for entry in timetable
        )

    def faculty_conflicts(self, timetable) -> int:
        return self._count_duplicate_keys(
            (entry["Faculty"], entry["Day"], int(entry["Time"]))
            for entry in timetable
        )

    def room_conflicts(self, timetable) -> int:
        return self._count_duplicate_keys(
            (entry["Room"], entry["Day"], int(entry["Time"]))
            for entry in timetable
        )

    def subject_conflicts(self, timetable) -> int:
        return self._count_duplicate_keys(
            (entry["Section"], entry["Course"], entry["Day"], int(entry["Time"]))
            for entry in timetable
        )

    def faculty_workload_conflicts(self, timetable, dataset) -> int:
        workload: Dict[Tuple[str, str], int] = defaultdict(int)
        for entry in timetable:
            workload[(entry["Faculty"], entry["Day"])] += 1

        conflicts = 0
        for faculty, limit in dataset.faculty_daily_limits.items():
            for day in dataset.get_days():
                count = workload.get((faculty, day), 0)
                if count > limit:
                    conflicts += count - limit
        return conflicts

    def hours_conflicts(self, timetable, dataset) -> int:
        expected = {
            (row["Section"], row["SubjectID"]): int(row["HoursPerWeek"])
            for _, row in dataset.get_subjects().iterrows()
        }
        actual = Counter((entry["Section"], entry["SubjectID"]) for entry in timetable)
        conflicts = 0
        for key, hours in expected.items():
            conflicts += abs(actual.get(key, 0) - hours)
        return conflicts

    def room_type_conflicts(self, timetable, dataset) -> int:
        conflicts = 0
        for entry in timetable:
            room_type = dataset.room_types.get(entry["Room"], "Theory").lower()
            subject_type = str(entry.get("Type", "Theory")).lower()
            if room_type != subject_type:
                conflicts += 1
        return conflicts

    def total_conflicts(self, timetable, dataset) -> int:
        details = self.detailed_conflicts(timetable, dataset)
        return sum(details.values())

    def detailed_conflicts(self, timetable, dataset) -> dict:
        return {
            "section_conflicts": self.section_conflicts(timetable),
            "faculty_conflicts": self.faculty_conflicts(timetable),
            "room_conflicts": self.room_conflicts(timetable),
            "duplicate_subject_conflicts": self.subject_conflicts(timetable),
            "hours_conflicts": self.hours_conflicts(timetable, dataset),
            "faculty_workload_conflicts": self.faculty_workload_conflicts(
                timetable,
                dataset,
            ),
            "room_type_conflicts": self.room_type_conflicts(timetable, dataset),
        }

    def has_hard_conflicts(self, timetable, dataset) -> bool:
        details = self.detailed_conflicts(timetable, dataset)
        return any(value > 0 for value in details.values())
