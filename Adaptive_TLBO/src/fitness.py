"""Weighted fitness function for Adaptive TLBO timetable optimization."""

from __future__ import annotations

from collections import Counter, defaultdict
from statistics import pstdev

from constraint_checker import ConstraintChecker
from dynamic_priority import DynamicPriority
from faculty_satisfaction import FacultySatisfaction


class Fitness:
    """Evaluates timetables using hard-constraint penalties and soft rewards."""

    HARD_CONFLICT_PENALTY = 350.0

    def __init__(
        self,
        dataset,
        use_dynamic_priority: bool = True,
        use_faculty_satisfaction: bool = True,
        use_conflict_prediction: bool = True,
    ):
        self.dataset = dataset
        self.use_dynamic_priority = use_dynamic_priority
        self.use_faculty_satisfaction = use_faculty_satisfaction
        self.use_conflict_prediction = use_conflict_prediction
        self.constraint_checker = ConstraintChecker()
        self.faculty_satisfaction = FacultySatisfaction(dataset)
        self.dynamic_priority = DynamicPriority(dataset)
        self.cache = {}

    def clear_cache(self) -> None:
        self.cache.clear()

    def evaluate(self, timetable) -> float:
        key = tuple(
            (
                entry["Section"],
                entry["SubjectID"],
                entry["Faculty"],
                entry["Room"],
                entry["Day"],
                int(entry["Time"]),
            )
            for entry in timetable
        )
        if key in self.cache:
            return self.cache[key]

        conflicts = self.constraint_checker.total_conflicts(timetable, self.dataset)
        satisfaction = self.faculty_satisfaction.calculate(timetable) if self.use_faculty_satisfaction else 0.0
        priority = self.dynamic_priority.calculate(timetable) if self.use_dynamic_priority else 0.0
        workload = self._balanced_faculty_workload(timetable)
        room_utilization = self._balanced_room_utilization(timetable)
        daily_balance = self._balanced_daily_schedule(timetable)
        continuity = self._section_continuity(timetable)
        completion = self._completion_score(timetable)

        components = [(workload, 0.15), (room_utilization, 0.12),
                      (daily_balance, 0.12), (continuity, 0.09), (completion, 0.10)]
        if self.use_faculty_satisfaction:
            components.append((satisfaction, 0.22))
        if self.use_dynamic_priority:
            components.append((priority, 0.20))
        # A common additive scale keeps ablation variants comparable.  The
        # former per-variant normalization diluted valid added objectives.
        soft_score = sum(value * weight for value, weight in components)
        conflict_penalty = self.HARD_CONFLICT_PENALTY if self.use_conflict_prediction else 175.0
        fitness = soft_score - conflicts * conflict_penalty
        fitness = round(max(0.0, fitness), 4)
        self.cache[key] = fitness
        return fitness

    def _balanced_faculty_workload(self, timetable) -> float:
        counts = Counter(entry["Faculty"] for entry in timetable)
        if not counts:
            return 0.0
        values = list(counts.values())
        if len(values) == 1:
            return 100.0
        return round(max(0.0, 100.0 - pstdev(values) * 8), 2)

    def _balanced_room_utilization(self, timetable) -> float:
        counts = Counter(entry["Room"] for entry in timetable)
        if not counts:
            return 0.0
        values = list(counts.values())
        if len(values) == 1:
            return 100.0
        return round(max(0.0, 100.0 - pstdev(values) * 6), 2)

    def _balanced_daily_schedule(self, timetable) -> float:
        section_day_counts = defaultdict(int)
        for entry in timetable:
            section_day_counts[(entry["Section"], entry["Day"])] += 1
        if not section_day_counts:
            return 0.0
        values = list(section_day_counts.values())
        return round(max(0.0, 100.0 - pstdev(values) * 12), 2)

    def _section_continuity(self, timetable) -> float:
        idle_gaps = 0
        possible = 0
        grouped = defaultdict(list)
        for entry in timetable:
            grouped[(entry["Section"], entry["Day"])].append(int(entry["Time"]))
        for periods in grouped.values():
            periods = sorted(periods)
            if len(periods) <= 1:
                continue
            possible += len(periods) - 1
            for left, right in zip(periods, periods[1:]):
                if right - left > 1:
                    idle_gaps += right - left - 1
        if possible == 0:
            return 100.0
        return round(max(0.0, 100.0 - (idle_gaps / possible) * 25), 2)

    def _completion_score(self, timetable) -> float:
        expected = {
            (row["Section"], row["SubjectID"]): int(row["HoursPerWeek"])
            for _, row in self.dataset.get_subjects().iterrows()
        }
        actual = Counter((entry["Section"], entry["SubjectID"]) for entry in timetable)
        if not expected:
            return 0.0
        satisfied = sum(1 for key, hours in expected.items() if actual.get(key, 0) == hours)
        return round((satisfied / len(expected)) * 100, 2)
