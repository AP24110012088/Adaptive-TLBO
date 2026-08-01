"""Teacher phase for the Adaptive TLBO optimizer."""

from __future__ import annotations

import copy


class TeacherPhase:
    """Moves learners toward the best timetable while respecting constraints."""

    def __init__(self, fitness, generator=None, rng=None):
        self.fitness = fitness
        self.generator = generator
        self.random = rng

    def improve(self, population, teaching_factor: float = 1.5, use_dynamic_priority: bool = True):
        teacher = max(population, key=self.fitness.evaluate)
        teacher_score = self.fitness.evaluate(teacher)
        new_population = []

        for timetable in population:
            base_score = self.fitness.evaluate(timetable)
            candidate = copy.deepcopy(timetable)
            influence = min(0.75, 0.25 + teaching_factor * 0.20)

            for index, lecture in enumerate(candidate):
                if self.random.random() > influence:
                    continue
                teacher_lecture = teacher[index]
                if lecture["Section"] != teacher_lecture["Section"]:
                    continue
                lecture["Day"] = teacher_lecture["Day"]
                lecture["Time"] = int(teacher_lecture["Time"])
                lecture["Period"] = f"P{int(teacher_lecture['Time'])}"
                if self.random.random() < 0.5:
                    lecture["Room"] = teacher_lecture["Room"]

            if use_dynamic_priority and self.random.random() < 0.35 and candidate:
                high_priority = max(candidate, key=lambda item: int(item["Priority"]))
                preferred = self.fitness.dataset.preferred_periods(high_priority["Faculty"])
                high_priority["Time"] = self.random.choice(preferred)
                high_priority["Period"] = f"P{int(high_priority['Time'])}"

            if self.generator is not None:
                candidate = self.generator.repair(candidate)

            candidate_score = self.fitness.evaluate(candidate)
            if candidate_score >= base_score or candidate_score >= teacher_score:
                new_population.append(candidate)
            else:
                new_population.append(timetable)

        return new_population
