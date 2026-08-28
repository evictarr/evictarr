from pydantic import BaseModel

from app.db.models import RuleType, SeriesGranularity, ThresholdUnit


class RuleOut(BaseModel):
    id: int
    name: str
    rule_type: RuleType
    enabled: bool
    threshold_value: int
    threshold_unit: ThresholdUnit
    granularity: SeriesGranularity | None
    exempt_favorite: bool


class RuleCreateRequest(BaseModel):
    name: str
    rule_type: RuleType
    threshold_value: int
    threshold_unit: ThresholdUnit
    granularity: SeriesGranularity | None = None
    exempt_favorite: bool = True
    enabled: bool = True


class RuleUpdateRequest(BaseModel):
    name: str
    threshold_value: int
    threshold_unit: ThresholdUnit
    granularity: SeriesGranularity | None = None
    exempt_favorite: bool = True
    enabled: bool = True
