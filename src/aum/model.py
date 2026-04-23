from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Window:
    label: str
    used_percent: float
    resets_at: Optional[int] = None
    extra: str = ""


@dataclass
class ProviderResult:
    provider: str
    plan: Optional[str] = None
    account: Optional[str] = None
    windows: list[Window] = field(default_factory=list)
    error: Optional[str] = None
    stale_seconds: Optional[int] = None
