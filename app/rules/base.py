from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RuleContext:
    impossible_travel_speed_kmh: float | None = None
    consecutive_failures: int = 0
    distinct_users_per_ip: int = 0
    is_new_device: bool = False
    is_new_country: bool = False
    is_high_risk_ip: bool = False
    time_deviation_hours: int | None = None


@dataclass(frozen=True, slots=True)
class Rule(ABC):
    name: str
    weight: int

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("rule name cannot be empty")
        if isinstance(self.weight, bool) or not isinstance(self.weight, int):
            raise TypeError("rule weight must be an integer")
        if not 0 <= self.weight <= 100:
            raise ValueError("rule weight must be between 0 and 100")

    @abstractmethod
    def condition(self, context: RuleContext) -> bool:
        raise NotImplementedError
