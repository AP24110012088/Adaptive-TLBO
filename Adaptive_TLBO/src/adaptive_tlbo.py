"""Adaptive Teaching Learning Based Optimization for timetabling."""

from __future__ import annotations

import copy
import logging
import random
import time
from typing import Dict, List, Tuple

from fitness import Fitness
from learner_phase import LearnerPhase
from teacher_phase import TeacherPhase
from timetable_generator import TimetableGenerator


class AdaptiveTLBO:
    """Optimizes timetables using adaptive teacher, learner and mutation phases."""

    def __init__(
        self,
        dataset,
        population_size: int = 30,
        iterations: int = 50,
        early_stopping_rounds: int | None = None,
        improvement_threshold: float = 1e-3,
        random_seed: int | None = 42,
        use_dynamic_priority: bool = True,
        use_faculty_satisfaction: bool = True,
        use_adaptive_parameters: bool = True,
        use_conflict_prediction: bool = True,
        verbose: bool = True,
    ):
        self.dataset = dataset
        self.population_size = population_size
        self.iterations = iterations
        self.early_stopping_rounds = early_stopping_rounds
        self.improvement_threshold = improvement_threshold
        self.logger = logging.getLogger("adaptive_tlbo")
        self.random = random.Random(random_seed)
        self.generator = TimetableGenerator(dataset, random_seed=random_seed, prioritize_subjects=use_dynamic_priority, honor_faculty_preferences=use_faculty_satisfaction, strict_conflict_repair=use_conflict_prediction)
        self.fitness = Fitness(
            dataset,
            use_dynamic_priority=use_dynamic_priority,
            use_faculty_satisfaction=use_faculty_satisfaction,
            use_conflict_prediction=use_conflict_prediction,
        )
        self.teacher_phase = TeacherPhase(self.fitness, self.generator, self.random)
        self.learner_phase = LearnerPhase(self.fitness, self.generator, self.random)
        self.early_stopped = False
        self.completed_iterations = 0
        self.history: List[Dict[str, float]] = []
        self.use_dynamic_priority = use_dynamic_priority
        self.use_faculty_satisfaction = use_faculty_satisfaction
        self.use_adaptive_parameters = use_adaptive_parameters
        self.use_conflict_prediction = use_conflict_prediction
        self.verbose = verbose

    def initialize_population(self):
        return [
            self.generator.generate_random_timetable()
            for _ in range(self.population_size)
        ]

    def get_best(self, population) -> Tuple[list, float]:
        scores = [self.fitness.evaluate(timetable) for timetable in population]
        best_index = max(range(len(population)), key=lambda idx: scores[idx])
        return copy.deepcopy(population[best_index]), scores[best_index]

    def _elite_local_search(self, elite, intensity: int):
        """Perform bounded, strictly improving variable-neighbourhood search."""
        best = copy.deepcopy(elite)
        best_score = self.fitness.evaluate(best)
        periods = self.dataset.get_periods()
        rooms = self.dataset.get_rooms()["RoomID"].astype(str).tolist()

        for _ in range(intensity):
            improved = False
            for move in range(4):
                candidate = copy.deepcopy(best)
                if not candidate:
                    break
                first = self.random.randrange(len(candidate))
                if move == 0 and len(candidate) > 1:
                    second = self.random.randrange(len(candidate))
                    while second == first:
                        second = self.random.randrange(len(candidate))
                    for field in ("Day", "Time", "Period"):
                        candidate[first][field], candidate[second][field] = (
                            candidate[second][field], candidate[first][field]
                        )
                elif move == 1:
                    candidate[first]["Time"] = self.random.choice(periods)
                    candidate[first]["Period"] = f"P{candidate[first]['Time']}"
                elif move == 2 and rooms:
                    candidate[first]["Room"] = self.random.choice(rooms)
                else:
                    second = self.random.randrange(len(candidate))
                    candidate[first]["Day"], candidate[second]["Day"] = (
                        candidate[second]["Day"], candidate[first]["Day"]
                    )
                candidate = self.generator.repair(candidate)
                score = self.fitness.evaluate(candidate)
                if score > best_score + self.improvement_threshold:
                    best, best_score, improved = candidate, score, True
            if not improved:
                break
        return best, best_score

    def optimize(self):
        population = self.initialize_population()
        best_solution, best_fitness = self.get_best(population)
        stagnant_rounds = 0

        for iteration in range(1, self.iterations + 1):
            iteration_started = time.perf_counter()
            self.fitness.clear_cache()
            progress = iteration / max(1, self.iterations)
            if self.use_adaptive_parameters:
                teaching_factor = 1.0 + (1.0 - progress)
                learning_factor = 0.55 - (0.25 * progress)
                # Smooth exponential decay: explore early, exploit late.
                mutation_rate = 0.035 + 0.30 * ((1.0 - progress) ** 2)
            else:
                teaching_factor, learning_factor, mutation_rate = 1.5, 0.40, 0.15

            scores = [self.fitness.evaluate(item) for item in population]
            elite_count = max(1, int(round(self.population_size * 0.20)))
            elite_indices = sorted(
                range(self.population_size), key=scores.__getitem__, reverse=True
            )[:elite_count]
            elites = [copy.deepcopy(population[index]) for index in elite_indices]

            population = self.teacher_phase.improve(
                population, teaching_factor, self.use_dynamic_priority,
            )
            population = self.learner_phase.improve(population, learning_factor)
            final_phase = progress >= 0.70
            population = [
                self.generator.mutate(timetable, mutation_rate)
                if (self.use_adaptive_parameters and not final_phase
                    and self.random.random() < 0.80) else timetable
                for timetable in population
            ]

            # Strong elitism: the best 20% is carried forward unchanged.
            for index, elite in zip(elite_indices, elites):
                population[index] = elite

            if self.use_adaptive_parameters:
                # Improve every protected elite independently.  A global-best
                # update happens immediately and is never reversed.
                for index in elite_indices:
                    candidate, candidate_score = self._elite_local_search(
                        population[index], intensity=3 if final_phase else 2,
                    )
                    if candidate_score > self.fitness.evaluate(population[index]):
                        population[index] = candidate
                    if candidate_score > best_fitness + self.improvement_threshold:
                        best_solution = copy.deepcopy(candidate)
                        best_fitness = candidate_score
                        stagnant_rounds = 0

            current_scores = [self.fitness.evaluate(timetable) for timetable in population]
            current_best_index = max(range(len(population)), key=current_scores.__getitem__)
            current_best = copy.deepcopy(population[current_best_index])
            current_score = current_scores[current_best_index]
            if current_score > best_fitness + self.improvement_threshold:
                best_solution = copy.deepcopy(current_best)
                best_fitness = current_score
                stagnant_rounds = 0
            else:
                stagnant_rounds += 1

            violation_score = self.fitness.constraint_checker.total_conflicts(
                best_solution, self.dataset,
            )
            conflicts = violation_score
            self.history.append(
                {
                    "Iteration": iteration,
                    "BestFitness": round(best_fitness, 4),
                    "AverageFitness": round(sum(current_scores) / len(current_scores), 4),
                    "WorstFitness": round(min(current_scores), 4),
                    "Conflicts": conflicts,
                    "ConstraintViolationScore": violation_score,
                    "FacultySatisfaction": round(
                        self.fitness.faculty_satisfaction.calculate(best_solution), 2,
                    ),
                    "TeachingFactor": round(teaching_factor, 4),
                    "LearningFactor": round(learning_factor, 4),
                    "MutationRate": round(mutation_rate, 4),
                    "IterationTimeSeconds": round(time.perf_counter() - iteration_started, 4),
                }
            )

            worst_index = min(range(len(population)), key=current_scores.__getitem__)
            population[worst_index] = copy.deepcopy(best_solution)

            refresh_threshold = (
                max(4, self.early_stopping_rounds // 2)
                if self.early_stopping_rounds is not None else 4
            )
            if (self.use_adaptive_parameters and not final_phase
                    and stagnant_rounds >= refresh_threshold):
                # Preserve elites and diversify only the worst quartile.
                ranked = sorted(range(len(population)), key=current_scores.__getitem__)
                refresh_count = max(1, int(round(self.population_size * 0.25)))
                protected = set(elite_indices)
                replaceable = [item for item in ranked if item not in protected]
                for index in replaceable[:refresh_count]:
                    # A repaired elite mutation is an informed immigrant: it
                    # preserves feasible structure while restoring diversity.
                    population[index] = self.generator.mutate(
                        best_solution, max(0.10, mutation_rate),
                    )

            if self.verbose:
                record = self.history[-1]
                print("=" * 52)
                print(f"Iteration {iteration:02d}/{self.iterations}")
                print("=" * 52)
                print(f"Current Best Fitness     : {record['BestFitness']:.2f}")
                print(f"Current Average Fitness  : {record['AverageFitness']:.2f}")
                print(f"Current Worst Fitness    : {record['WorstFitness']:.2f}")
                print(f"Conflicts                : {record['Conflicts']}")
                print(f"Constraint Violations    : {record['ConstraintViolationScore']}")
                print(f"Faculty Satisfaction     : {record['FacultySatisfaction']:.2f}%")
                print(f"Teaching Factor          : {record['TeachingFactor']:.2f}")
                print(f"Learning Factor          : {record['LearningFactor']:.2f}")
                print(f"Mutation Rate            : {record['MutationRate']:.2f}")
                print(f"Iteration Time           : {record['IterationTimeSeconds']:.2f} sec")
            self.completed_iterations = iteration
            if (iteration >= 15 and self.early_stopping_rounds is not None
                    and stagnant_rounds >= self.early_stopping_rounds):
                self.early_stopped = True
                break
        return best_solution, best_fitness, self.history

