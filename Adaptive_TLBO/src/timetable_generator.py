"""Section-wise timetable construction and neighbourhood operations."""

from __future__ import annotations

import copy
import random
from typing import Dict, List, Tuple


Lecture = Dict[str, object]


class TimetableGenerator:
    """Creates feasible timetables while respecting section, faculty and room use."""

    def __init__(self, dataset, random_seed: int | None = None, *, prioritize_subjects: bool = True, honor_faculty_preferences: bool = True, strict_conflict_repair: bool = True):
        self.dataset = dataset
        self.random = random.Random(random_seed)
        self.days = dataset.get_days()
        self.periods = dataset.get_periods()
        self.timeslots = [(day, period) for day in self.days for period in self.periods]
        self.rooms = dataset.get_rooms().to_dict("records")
        self.prioritize_subjects = prioritize_subjects
        self.honor_faculty_preferences = honor_faculty_preferences
        self.strict_conflict_repair = strict_conflict_repair
        self.preferred_period_map = {
            faculty: set(dataset.preferred_periods(faculty))
            for faculty in dataset.get_faculty()["FacultyName"].astype(str).tolist()
        }
        self.room_candidates = {
            room_type.lower(): [
                room for room in self.rooms
                if str(room.get("Type", "Theory")).lower() == room_type.lower()
            ]
            for room_type in {str(room.get("Type", "Theory")) for room in self.rooms}
        }

    def generate_random_timetable(self) -> List[Lecture]:
        """Build one complete timetable, scheduling every section independently."""

        timetable: List[Lecture] = []
        occupied_section: set[Tuple[str, str, int]] = set()
        occupied_faculty: set[Tuple[str, str, int]] = set()
        occupied_room: set[Tuple[str, str, int]] = set()
        faculty_daily_load: Dict[Tuple[str, str], int] = {}

        subjects = self.dataset.get_subjects().copy()
        if self.prioritize_subjects:
            subjects = subjects.sort_values(
                by=["Section", "Priority", "HoursPerWeek"],
                ascending=[True, False, False],
            )
        else:
            subjects = subjects.sample(
                frac=1.0, random_state=self.random.randrange(2**31 - 1)
            )

        for _, subject in subjects.iterrows():
            candidate_slots = self._ordered_slots(str(subject["Faculty"]))
            for _ in range(int(subject["HoursPerWeek"])):
                lecture = self._place_lecture(
                    subject,
                    candidate_slots,
                    occupied_section,
                    occupied_faculty,
                    occupied_room,
                    faculty_daily_load,
                )
                timetable.append(lecture)

        return self._coalesce_lab_blocks(self.repair(timetable))

    def _coalesce_lab_blocks(self, timetable: List[Lecture]) -> List[Lecture]:
        """Make a lab course occupy consecutive periods when free capacity permits."""
        groups: Dict[Tuple[str, str], List[Lecture]] = {}
        for lecture in timetable:
            if str(lecture.get("Type", "Theory")).lower() == "lab":
                groups.setdefault((str(lecture["Section"]), str(lecture["SubjectID"])), []).append(lecture)
        for entries in groups.values():
            if len(entries) < 2:
                continue
            others = [item for item in timetable if item not in entries]
            occupied = set()
            for item in others:
                occupied.add(("section", item["Section"], item["Day"], int(item["Time"])))
                occupied.add(("faculty", item["Faculty"], item["Day"], int(item["Time"])))
                occupied.add(("room", item["Room"], item["Day"], int(item["Time"])))
            placed = False
            for day in self.days:
                for start in self.periods:
                    block = list(range(start, start + len(entries)))
                    if any(period not in self.periods for period in block):
                        continue
                    keys = []
                    for period in block:
                        keys.extend([
                            ("section", entries[0]["Section"], day, period),
                            ("faculty", entries[0]["Faculty"], day, period),
                            ("room", entries[0]["Room"], day, period),
                        ])
                    if any(key in occupied for key in keys):
                        continue
                    for lecture, period in zip(entries, block):
                        lecture["Day"] = day
                        lecture["Time"] = period
                        lecture["Period"] = f"P{period}"
                    placed = True
                    break
                if placed:
                    break
        return timetable
    def _coalesce_lab_blocks(self, timetable: List[Lecture]) -> List[Lecture]:
        """Place all hourly entries of one lab in consecutive periods if feasible."""
        groups = {}
        for item in timetable:
            if str(item.get("Type", "Theory")).lower() == "lab":
                groups.setdefault((item["Section"], item["SubjectID"]), []).append(item)
        for entries in groups.values():
            others = [item for item in timetable if item not in entries]
            used = {(kind, item[key], item["Day"], int(item["Time"])) for item in others for kind, key in (("section", "Section"), ("faculty", "Faculty"), ("room", "Room"))}
            for day in self.days:
                for start in self.periods:
                    block = list(range(start, start + len(entries)))
                    if any(period not in self.periods for period in block):
                        continue
                    keys = [(kind, entries[0][key], day, period) for period in block for kind, key in (("section", "Section"), ("faculty", "Faculty"), ("room", "Room"))]
                    if any(key in used for key in keys):
                        continue
                    for item, period in zip(entries, block):
                        item["Day"], item["Time"], item["Period"] = day, period, f"P{period}"
                    break
                else:
                    continue
                break
        return timetable
    def _ordered_slots(self, faculty_name: str) -> List[Tuple[str, int]]:
        preferred = self.preferred_period_map.get(faculty_name, set(self.periods)) if self.honor_faculty_preferences else set(self.periods)
        slots = self.timeslots[:]
        self.random.shuffle(slots)
        slots.sort(key=lambda item: (item[1] not in preferred, self.random.random()))
        return slots

    def _place_lecture(
        self,
        subject,
        candidate_slots: List[Tuple[str, int]],
        occupied_section: set[Tuple[str, str, int]],
        occupied_faculty: set[Tuple[str, str, int]],
        occupied_room: set[Tuple[str, str, int]],
        faculty_daily_load: Dict[Tuple[str, str], int],
    ) -> Lecture:
        best_choice: tuple[int, str, int, str] | None = None
        faculty_name = str(subject["Faculty"])
        section = str(subject["Section"])
        subject_type = str(subject.get("Type", "Theory"))

        for day, period in candidate_slots:
            for room in self._candidate_rooms(subject_type):
                room_id = str(room["RoomID"])
                penalty = self._placement_penalty(
                    section,
                    faculty_name,
                    room_id,
                    day,
                    period,
                    subject_type,
                    occupied_section,
                    occupied_faculty,
                    occupied_room,
                    faculty_daily_load,
                )
                if best_choice is None or penalty < best_choice[0]:
                    best_choice = (penalty, day, period, room_id)
                if penalty == 0:
                    return self._commit(
                        subject,
                        day,
                        period,
                        room_id,
                        occupied_section,
                        occupied_faculty,
                        occupied_room,
                        faculty_daily_load,
                    )

        assert best_choice is not None
        _, day, period, room_id = best_choice
        return self._commit(
            subject,
            day,
            period,
            room_id,
            occupied_section,
            occupied_faculty,
            occupied_room,
            faculty_daily_load,
        )

    def _candidate_rooms(self, subject_type: str) -> List[dict]:
        matching = self.room_candidates.get(subject_type.lower(), [])
        rooms = matching or self.rooms
        rooms = rooms[:]
        self.random.shuffle(rooms)
        return rooms

    def _placement_penalty(
        self,
        section: str,
        faculty_name: str,
        room_id: str,
        day: str,
        period: int,
        subject_type: str,
        occupied_section: set[Tuple[str, str, int]],
        occupied_faculty: set[Tuple[str, str, int]],
        occupied_room: set[Tuple[str, str, int]],
        faculty_daily_load: Dict[Tuple[str, str], int],
    ) -> int:
        penalty = 0
        if (section, day, period) in occupied_section:
            penalty += 1000
        if (faculty_name, day, period) in occupied_faculty:
            penalty += 900
        if (room_id, day, period) in occupied_room:
            penalty += 800
        room_type = self.dataset.room_types.get(room_id, "Theory")
        if room_type.lower() != subject_type.lower():
            penalty += 20
        daily_limit = self.dataset.faculty_daily_limits.get(faculty_name, 3)
        if faculty_daily_load.get((faculty_name, day), 0) >= daily_limit:
            penalty += 30
        if self.honor_faculty_preferences and period not in self.preferred_period_map.get(faculty_name, set(self.periods)):
            penalty += 5
        return penalty

    def _commit(
        self,
        subject,
        day: str,
        period: int,
        room_id: str,
        occupied_section: set[Tuple[str, str, int]],
        occupied_faculty: set[Tuple[str, str, int]],
        occupied_room: set[Tuple[str, str, int]],
        faculty_daily_load: Dict[Tuple[str, str], int],
    ) -> Lecture:
        section = str(subject["Section"])
        faculty_name = str(subject["Faculty"])
        occupied_section.add((section, day, period))
        occupied_faculty.add((faculty_name, day, period))
        occupied_room.add((room_id, day, period))
        faculty_daily_load[(faculty_name, day)] = (
            faculty_daily_load.get((faculty_name, day), 0) + 1
        )
        return {
            "Section": section,
            "SubjectID": str(subject["SubjectID"]),
            "Course": str(subject["SubjectName"]),
            "Faculty": faculty_name,
            "Room": room_id,
            "Day": day,
            "Time": int(period),
            "Period": f"P{int(period)}",
            "Hours": int(subject["HoursPerWeek"]),
            "Priority": int(subject["Priority"]),
            "Type": str(subject.get("Type", "Theory")),
        }

    def mutate(self, timetable: List[Lecture], mutation_rate: float) -> List[Lecture]:
        candidate = copy.deepcopy(timetable)
        if not candidate:
            return candidate

        for lecture in candidate:
            if self.random.random() > mutation_rate:
                continue
            if self.random.random() < 0.65:
                day, period = self.random.choice(self.timeslots)
                lecture["Day"] = day
                lecture["Time"] = int(period)
                lecture["Period"] = f"P{int(period)}"
            else:
                lecture["Room"] = str(self.random.choice(self.rooms)["RoomID"])

        return self.repair(candidate)

    def repair(self, timetable: List[Lecture]) -> List[Lecture]:
        """Repair section, faculty and room clashes using fast local reassignment."""

        candidate = copy.deepcopy(timetable)
        occupied_section: set[Tuple[str, str, int]] = set()
        occupied_faculty: set[Tuple[str, str, int]] = set()
        occupied_room: set[Tuple[str, str, int]] = set()

        for lecture in sorted(candidate, key=lambda item: -int(item["Priority"])):
            if self._lecture_is_free(
                lecture,
                occupied_section,
                occupied_faculty,
                occupied_room,
            ):
                self._occupy(lecture, occupied_section, occupied_faculty, occupied_room)
                continue

            replacement = self._find_free_slot(
                lecture,
                occupied_section,
                occupied_faculty,
                occupied_room,
            )
            if replacement:
                day, period, room = replacement
                lecture["Day"] = day
                lecture["Time"] = period
                lecture["Period"] = f"P{period}"
                lecture["Room"] = room
            self._occupy(lecture, occupied_section, occupied_faculty, occupied_room)

        return self._repair_faculty_workload(candidate) if self.strict_conflict_repair else candidate

    def _lecture_is_free(
        self,
        lecture: Lecture,
        occupied_section: set[Tuple[str, str, int]],
        occupied_faculty: set[Tuple[str, str, int]],
        occupied_room: set[Tuple[str, str, int]],
    ) -> bool:
        day = str(lecture["Day"])
        period = int(lecture["Time"])
        return (
            (str(lecture["Section"]), day, period) not in occupied_section
            and (str(lecture["Faculty"]), day, period) not in occupied_faculty
            and (str(lecture["Room"]), day, period) not in occupied_room
        )

    def _find_free_slot(
        self,
        lecture: Lecture,
        occupied_section: set[Tuple[str, str, int]],
        occupied_faculty: set[Tuple[str, str, int]],
        occupied_room: set[Tuple[str, str, int]],
    ) -> tuple[str, int, str] | None:
        slots = self._ordered_slots(str(lecture["Faculty"]))
        for day, period in slots:
            for room in self._candidate_rooms(str(lecture.get("Type", "Theory"))):
                probe = dict(lecture)
                probe["Day"] = day
                probe["Time"] = period
                probe["Room"] = str(room["RoomID"])
                if self._lecture_is_free(
                    probe,
                    occupied_section,
                    occupied_faculty,
                    occupied_room,
                ):
                    return day, period, str(room["RoomID"])
        return None

    @staticmethod
    def _occupy(
        lecture: Lecture,
        occupied_section: set[Tuple[str, str, int]],
        occupied_faculty: set[Tuple[str, str, int]],
        occupied_room: set[Tuple[str, str, int]],
    ) -> None:
        day = str(lecture["Day"])
        period = int(lecture["Time"])
        occupied_section.add((str(lecture["Section"]), day, period))
        occupied_faculty.add((str(lecture["Faculty"]), day, period))
        occupied_room.add((str(lecture["Room"]), day, period))

    def _repair_faculty_workload(self, timetable: List[Lecture]) -> List[Lecture]:
        """Move overload lectures to days where the faculty has spare capacity."""

        for _ in range(5):
            moved = False
            section_occ, faculty_occ, room_occ, daily_load = self._occupancy(timetable)
            overloads = [
                (faculty, day, load - self.dataset.faculty_daily_limits.get(faculty, 3))
                for (faculty, day), load in daily_load.items()
                if load > self.dataset.faculty_daily_limits.get(faculty, 3)
            ]
            if not overloads:
                break

            for faculty, day, excess in overloads:
                lectures = [
                    lecture for lecture in timetable
                    if lecture["Faculty"] == faculty and lecture["Day"] == day
                ]
                lectures.sort(key=lambda item: int(item["Priority"]))
                for lecture in lectures[:excess]:
                    replacement = self._find_workload_slot(
                        lecture,
                        section_occ,
                        faculty_occ,
                        room_occ,
                        daily_load,
                    )
                    if replacement is None:
                        continue
                    old_key = (
                        lecture["Section"],
                        lecture["Faculty"],
                        lecture["Room"],
                        lecture["Day"],
                        int(lecture["Time"]),
                    )
                    new_day, new_period, new_room = replacement
                    section_occ.discard((old_key[0], old_key[3], old_key[4]))
                    faculty_occ.discard((old_key[1], old_key[3], old_key[4]))
                    room_occ.discard((old_key[2], old_key[3], old_key[4]))
                    daily_load[(old_key[1], old_key[3])] -= 1

                    lecture["Day"] = new_day
                    lecture["Time"] = int(new_period)
                    lecture["Period"] = f"P{int(new_period)}"
                    lecture["Room"] = new_room
                    section_occ.add((lecture["Section"], new_day, int(new_period)))
                    faculty_occ.add((lecture["Faculty"], new_day, int(new_period)))
                    room_occ.add((new_room, new_day, int(new_period)))
                    daily_load[(lecture["Faculty"], new_day)] = (
                        daily_load.get((lecture["Faculty"], new_day), 0) + 1
                    )
                    moved = True
            if not moved:
                break
        return timetable

    def _find_workload_slot(
        self,
        lecture: Lecture,
        section_occ: set[Tuple[str, str, int]],
        faculty_occ: set[Tuple[str, str, int]],
        room_occ: set[Tuple[str, str, int]],
        daily_load: Dict[Tuple[str, str], int],
    ) -> tuple[str, int, str] | None:
        faculty = str(lecture["Faculty"])
        limit = self.dataset.faculty_daily_limits.get(faculty, 3)
        for day, period in self._ordered_slots(faculty):
            if daily_load.get((faculty, day), 0) >= limit:
                continue
            if (str(lecture["Section"]), day, period) in section_occ:
                continue
            if (faculty, day, period) in faculty_occ:
                continue
            for room in self._candidate_rooms(str(lecture.get("Type", "Theory"))):
                room_id = str(room["RoomID"])
                if (room_id, day, period) not in room_occ:
                    return day, period, room_id
        return None

    def _occupancy(self, timetable: List[Lecture]):
        section_occ = set()
        faculty_occ = set()
        room_occ = set()
        daily_load: Dict[Tuple[str, str], int] = {}
        for lecture in timetable:
            day = str(lecture["Day"])
            period = int(lecture["Time"])
            section_occ.add((str(lecture["Section"]), day, period))
            faculty_occ.add((str(lecture["Faculty"]), day, period))
            room_occ.add((str(lecture["Room"]), day, period))
            key = (str(lecture["Faculty"]), day)
            daily_load[key] = daily_load.get(key, 0) + 1
        return section_occ, faculty_occ, room_occ, daily_load




