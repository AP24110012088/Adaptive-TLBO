"""Dynamic priority scoring for Adaptive TLBO."""

from __future__ import annotations


class DynamicPriority:
    """Rewards high-priority subjects in productive days and periods."""

    def __init__(self, dataset):
        self.dataset = dataset

    def calculate(self, timetable) -> float:
        if not timetable:
            return 0.0

        score = 0.0
        maximum = 0.0
        for lecture in timetable:
            priority = int(lecture.get("Priority", 1))
            period = int(lecture["Time"])
            day = lecture["Day"]
            multiplier = 1.0
            if priority >= 5 and day in {"Monday", "Tuesday", "Wednesday"}:
                multiplier += 0.20
            if priority >= 4 and period <= 3:
                multiplier += 0.15
            if period == 6 and priority >= 5:
                multiplier -= 0.10
            score += priority * multiplier
            maximum += priority * 1.35

        if maximum == 0:
            return 0.0
        return round((score / maximum) * 100, 2)

    def calculate_priority_score(self, timetable) -> float:
        return self.calculate(timetable)
