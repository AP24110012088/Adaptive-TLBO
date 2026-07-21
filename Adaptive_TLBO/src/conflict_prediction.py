class ConflictPrediction:

    def __init__(self):
        pass

    def predict(self, timetable):

        faculty_conflicts = 0
        room_conflicts = 0

        faculty_schedule = {}
        room_schedule = {}

        for lecture in timetable:

            faculty_key = (
                lecture["Faculty"],
                lecture["Day"],
                lecture["Time"]
            )

            room_key = (
                lecture["Room"],
                lecture["Day"],
                lecture["Time"]
            )

            if faculty_key in faculty_schedule:
                faculty_conflicts += 1
            else:
                faculty_schedule[faculty_key] = True

            if room_key in room_schedule:
                room_conflicts += 1
            else:
                room_schedule[room_key] = True

        return {
            "Faculty Conflicts": faculty_conflicts,
            "Room Conflicts": room_conflicts,
            "Total Conflicts": faculty_conflicts + room_conflicts
        }