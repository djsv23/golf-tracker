from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class HoleData:
    number: int
    par: int
    stroke_index: int
    yardage: Optional[int] = None


@dataclass(frozen=True)
class TeeSetData:
    name: str
    gender: str  # 'M' or 'F'
    par: Optional[int]
    course_rating: Optional[float]
    slope_rating: Optional[int]
    yardage: Optional[int]
    meters: Optional[int]
    hole_count: int
    holes: tuple  # tuple[HoleData, ...]


@dataclass(frozen=True)
class CourseSummary:
    external_id: str
    club_name: str
    course_name: str
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None


@dataclass(frozen=True)
class CourseDetail:
    external_id: str
    club_name: str
    course_name: str
    address: Optional[str]
    city: Optional[str]
    state: Optional[str]
    country: Optional[str]
    scorecard_url: Optional[str]
    tee_sets: tuple  # tuple[TeeSetData, ...]


class CourseProviderError(Exception):
    """Base error for course provider failures."""


class CourseProviderNotFound(CourseProviderError):
    """No course exists for the given external id."""


class CourseProviderQuotaExceeded(CourseProviderError):
    """The provider's request quota has been exhausted."""


class CourseProviderUnavailable(CourseProviderError):
    """The provider is not configured, or the plan tier forbids this call."""


class CourseProvider(ABC):
    source_name: str = 'local'

    @abstractmethod
    def search(self, query: str) -> list:
        """Return a list of CourseSummary matching the free-text query."""

    @abstractmethod
    def fetch(self, external_id: str) -> CourseDetail:
        """Return the full CourseDetail for a single course by external id."""
