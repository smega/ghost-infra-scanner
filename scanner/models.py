from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone


@dataclass
class Finding:
    resource_type: str
    resource_id: str
    region: str
    reason: str
    estimated_monthly_cost_usd: float
    detected_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict = field(default_factory=dict)
    console_url: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)
