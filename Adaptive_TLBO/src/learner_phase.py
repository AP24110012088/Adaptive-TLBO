"""Learner phase for Adaptive TLBO."""

from __future__ import annotations

import copy



class LearnerPhase:
    """Learners exchange allocation patterns with better peer timetables."""

    def __init__(self, fitness, generator=None, rng=None):
        self.fitness = fitness
        self.generator = generator
        self.random = rng

    def improve(self, population, learning_factor: float = 0.4):
        scores = [self.fitness.evaluate(timetable) for timetable in population]
        new_population = []

        for index, timetable in enumerate(population):
            partner_index = self.random.randrange(len(population))
            while partner_index == index and len(population) > 1:
                partner_index = self.random.randrange(len(population))

            learner = copy.deepcopy(timetable)
            partner = population[partner_index]
            take_from_partner = scores[partner_index] >= scores[index]
            exchange_rate = min(0.70, max(0.15, learning_factor))

            for lecture_index, lecture in enumerate(learner):
                if self.random.random() > exchange_rate:
                    continue
                peer = partner[lecture_index]
                if lecture["Section"] != peer["Section"]:
                    continue
                if take_from_partner:
                    lecture["Day"] = peer["Day"]
                    lecture["Time"] = int(peer["Time"])
                    lecture["Period"] = f"P{int(peer['Time'])}"
                    lecture["Room"] = peer["Room"]
                else:
                    lecture["Time"] = max(1, min(6, int(lecture["Time"]) + self.random.choice([-1, 1])))
                    lecture["Period"] = f"P{int(lecture['Time'])}"

            if self.generator is not None:
                learner = self.generator.repair(learner)

            if self.fitness.evaluate(learner) >= scores[index]:
                new_population.append(learner)
            else:
                new_population.append(timetable)

        return new_population

