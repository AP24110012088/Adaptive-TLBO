import random


class RepairOperator:

    def __init__(self, dataset, checker):

        self.dataset = dataset
        self.checker = checker

    def repair(self, timetable):

        rooms = list(self.dataset.get_rooms()["RoomID"])

        slots = self.dataset.get_timeslots()

        for lecture in timetable:

            while self.has_conflict(lecture, timetable):

                slot = slots.sample(1).iloc[0]

                lecture["Day"] = slot["Day"]
                lecture["Time"] = int(slot["Period"])
                lecture["Room"] = random.choice(rooms)

        return timetable

    def has_conflict(self, lecture, timetable):

        faculty = lecture["Faculty"]
        room = lecture["Room"]
        day = lecture["Day"]
        time = lecture["Time"]

        faculty_count = 0
        room_count = 0

        for other in timetable:

            if other is lecture:
                continue

            if (
                other["Faculty"] == faculty
                and other["Day"] == day
                and other["Time"] == time
            ):
                faculty_count += 1

            if (
                other["Room"] == room
                and other["Day"] == day
                and other["Time"] == time
            ):
                room_count += 1

        return faculty_count > 0 or room_count > 0