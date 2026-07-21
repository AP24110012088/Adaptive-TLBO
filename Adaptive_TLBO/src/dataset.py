"""Dataset loading and validation for the Adaptive TLBO timetable system."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import pandas as pd


class Dataset:
    """Loads CSV inputs and exposes cached lookup structures."""

    DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    PERIODS = [1, 2, 3, 4, 5, 6]
    REQUIRED_SUBJECT_COLUMNS = [
        "SubjectID",
        "SubjectName",
        "Faculty",
        "HoursPerWeek",
        "Priority",
        "Section",
    ]

    def __init__(self, data_dir: str | Path | None = None):
        project_root = Path(__file__).resolve().parents[1]
        self.data_dir = Path(data_dir) if data_dir else project_root / "data"
        self.subjects: pd.DataFrame | None = None
        self.faculty: pd.DataFrame | None = None
        self.rooms: pd.DataFrame | None = None
        self.timeslots: pd.DataFrame | None = None
        self.faculty_by_subject: Dict[str, str] = {}
        self.faculty_preferences: Dict[str, str] = {}
        self.faculty_daily_limits: Dict[str, int] = {}
        self.room_types: Dict[str, str] = {}

    def load_data(self) -> None:
        """Load, clean and validate all CSV files."""

        self.subjects = self._read_csv("subjects.csv")
        self.faculty = self._read_csv("faculty.csv")
        self.rooms = self._read_csv("rooms.csv")
        self.timeslots = self._read_csv("timeslots.csv")

        self._normalise_subjects()
        self._normalise_faculty()
        self._normalise_rooms()
        self._normalise_timeslots()
        self._validate()
        self._build_indexes()

    def _read_csv(self, name: str) -> pd.DataFrame:
        path = self.data_dir / name
        if not path.exists():
            raise FileNotFoundError(f"Required dataset file not found: {path}")
        df = pd.read_csv(path)
        df.columns = df.columns.str.strip()
        return df

    def _normalise_subjects(self) -> None:
        assert self.subjects is not None
        text_columns = ["SubjectID", "SubjectName", "Faculty", "Section", "Type"]
        for column in text_columns:
            if column in self.subjects.columns:
                self.subjects[column] = self.subjects[column].astype(str).str.strip()
        self.subjects["HoursPerWeek"] = self.subjects["HoursPerWeek"].astype(int)
        self.subjects["Priority"] = self.subjects["Priority"].astype(int)
        if "Type" not in self.subjects.columns:
            self.subjects["Type"] = "Theory"

    def _normalise_faculty(self) -> None:
        assert self.faculty is not None
        for column in ["FacultyID", "FacultyName", "SubjectID", "PreferredSlot"]:
            if column in self.faculty.columns:
                self.faculty[column] = self.faculty[column].astype(str).str.strip()
        self.faculty["MaxClassesPerDay"] = self.faculty["MaxClassesPerDay"].astype(int)

    def _normalise_rooms(self) -> None:
        assert self.rooms is not None
        for column in ["RoomID", "Type"]:
            if column in self.rooms.columns:
                self.rooms[column] = self.rooms[column].astype(str).str.strip()

    def _normalise_timeslots(self) -> None:
        assert self.timeslots is not None
        self.timeslots["Day"] = self.timeslots["Day"].astype(str).str.strip()
        self.timeslots["Period"] = self.timeslots["Period"].astype(int)

    def _validate(self) -> None:
        assert self.subjects is not None
        missing = [
            column for column in self.REQUIRED_SUBJECT_COLUMNS
            if column not in self.subjects.columns
        ]
        if missing:
            raise ValueError(
                "subjects.csv is missing required columns: "
                + ", ".join(missing)
            )
        if self.subjects.empty:
            raise ValueError("subjects.csv must contain at least one subject.")
        if self.rooms is not None and self.rooms.empty:
            raise ValueError("rooms.csv must contain at least one room.")
        if self.timeslots is not None and self.timeslots.empty:
            raise ValueError("timeslots.csv must contain at least one timeslot.")

    def _build_indexes(self) -> None:
        assert self.subjects is not None
        assert self.faculty is not None
        assert self.rooms is not None
        self.faculty_by_subject = {
            row["SubjectID"]: row["FacultyName"]
            for _, row in self.faculty.iterrows()
        }
        self.faculty_preferences = {
            row["FacultyName"]: str(row["PreferredSlot"]).lower()
            for _, row in self.faculty.iterrows()
        }
        self.faculty_daily_limits = {
            row["FacultyName"]: int(row["MaxClassesPerDay"])
            for _, row in self.faculty.iterrows()
        }
        self.room_types = {
            row["RoomID"]: str(row.get("Type", "Theory"))
            for _, row in self.rooms.iterrows()
        }

    def get_subjects(self) -> pd.DataFrame:
        assert self.subjects is not None
        return self.subjects

    def get_courses(self) -> pd.DataFrame:
        return self.get_subjects()

    def get_faculty(self) -> pd.DataFrame:
        assert self.faculty is not None
        return self.faculty

    def get_rooms(self) -> pd.DataFrame:
        assert self.rooms is not None
        return self.rooms

    def get_timeslots(self) -> pd.DataFrame:
        assert self.timeslots is not None
        return self.timeslots

    def get_sections(self) -> List[str]:
        return sorted(self.get_subjects()["Section"].unique().tolist())

    def get_days(self) -> List[str]:
        days = self.get_timeslots()["Day"].drop_duplicates().tolist()
        return days or self.DAYS

    def get_periods(self) -> List[int]:
        periods = sorted(
            self.get_timeslots()["Period"].drop_duplicates().astype(int).tolist()
        )
        return periods or self.PERIODS

    def get_subject_by_id(self, subject_id: str):
        result = self.get_subjects()[self.get_subjects()["SubjectID"] == subject_id]
        return None if result.empty else result.iloc[0]

    def get_faculty_by_subject(self, subject_id: str):
        result = self.get_faculty()[self.get_faculty()["SubjectID"] == subject_id]
        return None if result.empty else result.iloc[0]

    def preferred_periods(self, faculty_name: str) -> List[int]:
        preference = self.faculty_preferences.get(faculty_name, "").lower()
        periods = self.get_periods()
        midpoint = max(1, len(periods) // 2)
        if preference == "morning":
            return periods[:midpoint]
        if preference == "afternoon":
            return periods[midpoint:]
        return periods
