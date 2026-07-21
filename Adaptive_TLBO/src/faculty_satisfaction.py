"""Faculty preference and workload satisfaction scoring."""

from __future__ import annotations

from collections import defaultdict


class FacultySatisfaction:
    """Calculates a percentage score for faculty slot preference satisfaction."""

    def __init__(self, dataset):
        self.dataset = dataset
        self.preference_map = dataset.faculty_preferences
        self.daily_limits = dataset.faculty_daily_limits

    def calculate(self, timetable) -> float:
        if not timetable:
            return 0.0

        preference_points = 0.0
        workload = defaultdict(int)

        for lecture in timetable:
            faculty = lecture["Faculty"]
            period = int(lecture["Time"])
            preferred_periods = self.dataset.preferred_periods(faculty)
            if period in preferred_periods:
                preference_points += 1.0
            elif self.preference_map.get(faculty, "") not in {"morning", "afternoon"}:
                preference_points += 0.6
            else:
                preference_points += 0.25
            workload[(faculty, lecture["Day"])] += 1

        overload_penalty = 0.0
        for (faculty, _day), count in workload.items():
            limit = self.daily_limits.get(faculty, 3)
            if count > limit:
                overload_penalty += (count - limit) * 0.75

        raw = max(0.0, preference_points - overload_penalty)
        return round((raw / len(timetable)) * 100, 2)
