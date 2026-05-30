from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class SportType(Enum):
    CYCLING = "cycling"
    RUNNING = "running"
    HIKING = "hiking"
    WALKING = "walking"
    SWIMMING = "swimming"
    OTHER = "other"

    @classmethod
    def from_code(cls, code: int) -> "SportType":
        mapping = {1: cls.RUNNING, 2: cls.HIKING, 3: cls.CYCLING, 4: cls.WALKING, 5: cls.SWIMMING}
        return mapping.get(code, cls.OTHER)

    @classmethod
    def from_str(cls, value: str) -> "SportType":
        mapping = {
            "cycling": cls.CYCLING, "run": cls.RUNNING, "running": cls.RUNNING,
            "hiking": cls.HIKING, "walk": cls.WALKING, "walking": cls.WALKING,
            "swim": cls.SWIMMING, "swimming": cls.SWIMMING,
        }
        return mapping.get(value.lower(), cls.OTHER)

    @property
    def display(self) -> str:
        names = {
            "cycling": "骑行", "running": "跑步", "hiking": "徒步",
            "walking": "步行", "swimming": "游泳", "other": "其他",
        }
        return names.get(self.value, self.value)


class FileType(Enum):
    FIT = "fit"
    GPX = "gpx"
    UNKNOWN = "unknown"


@dataclass
class WorkoutInfo:
    id: int
    title: str = ""
    date: datetime | None = None
    distance_km: float = 0.0
    duration_seconds: int = 0
    sport_type: SportType = SportType.OTHER
    file_type: FileType = FileType.UNKNOWN
    file_url: str = ""
    avg_speed: float = 0.0
    selected: bool = False

    @property
    def duration_str(self) -> str:
        hours = self.duration_seconds // 3600
        minutes = (self.duration_seconds % 3600) // 60
        seconds = self.duration_seconds % 60
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes}:{seconds:02d}"

    @property
    def date_str(self) -> str:
        if self.date:
            return self.date.strftime("%Y-%m-%d %H:%M")
        return ""

    @property
    def distance_str(self) -> str:
        if self.distance_km >= 1:
            return f"{self.distance_km:.2f} km"
        return f"{self.distance_km * 1000:.0f} m"

    @property
    def avg_speed_str(self) -> str:
        if self.avg_speed > 0:
            return f"{self.avg_speed:.1f} km/h"
        return ""
