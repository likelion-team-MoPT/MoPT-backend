# campaigns/schemas.py (핵심 부분만)
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from ninja import Schema
from pydantic import ConfigDict, Field

from .models import Campaign


class CampaignDetailOut(Schema):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    status: Optional[str] = None
    channel: Optional[str] = None

    roas: Optional[float] = None
    spend: Optional[float] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    objectives: Optional[str] = None
    performance: Dict[str, Any] = Field(default_factory=dict)
    daily_performance: List[Dict[str, Any]] = Field(default_factory=list)
    duration: Dict[str, Optional[date]] = Field(default_factory=dict)
    creative: Dict[str, Any] = Field(default_factory=dict)

    # --- helpers ---
    @staticmethod
    def _to_float(v):
        if isinstance(v, Decimal):
            return float(v) if v.is_finite() else None
        if isinstance(v, (int, float)):
            return float(v)
        return None

    @staticmethod
    def _sanitize(obj):
        if isinstance(obj, Decimal):
            return float(obj) if obj.is_finite() else None
        if isinstance(obj, list):
            return [CampaignDetailOut._sanitize(x) for x in obj]
        if isinstance(obj, dict):
            # 키가 비문자(예: Decimal)면 JSON 직렬화를 위해 문자열화
            return {
                (str(k) if not isinstance(k, str) else k): CampaignDetailOut._sanitize(
                    v
                )
                for k, v in obj.items()
            }
        return obj

    @staticmethod
    def _to_date(v):
        if isinstance(v, datetime):
            return v.date()
        if isinstance(v, date):
            return v
        return None

    # --- resolvers ---
    @staticmethod
    def resolve_status(obj: Campaign) -> Optional[str]:
        v = getattr(obj, "status", None)
        return v.value if hasattr(v, "value") else (str(v) if v is not None else None)

    @staticmethod
    def resolve_channel(obj: Campaign) -> Optional[str]:
        v = getattr(obj, "channel", None)
        return v.value if hasattr(v, "value") else (str(v) if v is not None else None)

    @staticmethod
    def resolve_roas(obj: Campaign) -> Optional[float]:
        return CampaignDetailOut._to_float(getattr(obj, "roas", None))

    @staticmethod
    def resolve_spend(obj: Campaign) -> Optional[float]:
        return CampaignDetailOut._to_float(getattr(obj, "spend", None))

    @staticmethod
    def resolve_start_date(obj: Campaign) -> Optional[date]:
        return CampaignDetailOut._to_date(getattr(obj, "start_date", None))

    @staticmethod
    def resolve_end_date(obj: Campaign) -> Optional[date]:
        return CampaignDetailOut._to_date(getattr(obj, "end_date", None))

    @staticmethod
    def resolve_duration(obj: Campaign) -> Dict[str, Optional[date]]:
        return {
            "start_date": CampaignDetailOut._to_date(getattr(obj, "start_date", None)),
            "end_date": CampaignDetailOut._to_date(getattr(obj, "end_date", None)),
        }

    @staticmethod
    def resolve_performance(obj: Campaign) -> Dict[str, Any]:
        return CampaignDetailOut._sanitize(getattr(obj, "performance", None) or {})

    @staticmethod
    def resolve_creative(obj: Campaign) -> Dict[str, Any]:
        return CampaignDetailOut._sanitize(getattr(obj, "creative", None) or {})

    @staticmethod
    def resolve_daily_performance(obj: Campaign) -> List[Dict[str, Any]]:
        rel = getattr(obj, "daily_performances", None)
        if not rel:
            return []
        rows = list(
            rel.values("date", "impressions", "clicks", "spend", "sales", "roas")
        )
        return CampaignDetailOut._sanitize(rows)
