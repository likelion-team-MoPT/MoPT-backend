# campaigns/schemas.py
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional

from ninja import Schema
from pydantic import ConfigDict, Field

from .models import Campaign


class MessageOut(Schema):
    message: str


class PaginationMeta(Schema):
    page: int
    limit: int
    total: int


class CampaignListItemOut(Schema):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    channel: Optional[str] = None
    status: Optional[str] = None
    roas: Optional[float] = None
    spend: Optional[float] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class CampaignListOut(Schema):
    data: List[CampaignListItemOut]
    meta: PaginationMeta


class CampaignDetailOut(Schema):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    status: Optional[str] = None
    channel: Optional[str] = None

    # 리스트와 호환되는 필드
    roas: Optional[float] = None
    spend: Optional[float] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    objectives: Optional[str] = None
    performance: Dict[str, Any] = Field(default_factory=dict)
    daily_performance: List[Dict[str, Any]] = Field(default_factory=list)
    duration: Dict[str, Optional[date]] = Field(default_factory=dict)
    creative: Dict[str, Any] = Field(default_factory=dict)

    # --- resolvers (Decimal -> float 보장) ---
    @staticmethod
    def _to_float(v):
        if isinstance(v, Decimal):
            return float(v) if v.is_finite() else None
        if isinstance(v, (int, float)):
            return float(v)
        return None

    @staticmethod
    def resolve_roas(obj: Campaign) -> Optional[float]:
        return CampaignDetailOut._to_float(getattr(obj, "roas", None))

    @staticmethod
    def resolve_spend(obj: Campaign) -> Optional[float]:
        return CampaignDetailOut._to_float(getattr(obj, "spend", None))

    @staticmethod
    def resolve_start_date(obj: Campaign) -> Optional[date]:
        return getattr(obj, "start_date", None)

    @staticmethod
    def resolve_end_date(obj: Campaign) -> Optional[date]:
        return getattr(obj, "end_date", None)

    @staticmethod
    def resolve_duration(obj: Campaign) -> Dict[str, Optional[date]]:
        # 키를 start/end 대신 start_date/end_date로 통일
        return {
            "start_date": getattr(obj, "start_date", None),
            "end_date": getattr(obj, "end_date", None),
        }

    @staticmethod
    def resolve_performance(obj: Campaign) -> Dict[str, Any]:
        return getattr(obj, "performance", None) or {}

    @staticmethod
    def resolve_creative(obj: Campaign) -> Dict[str, Any]:
        return getattr(obj, "creative", None) or {}

    @staticmethod
    def resolve_daily_performance(obj: Campaign) -> List[Dict[str, Any]]:
        rel = getattr(obj, "daily_performances", None)
        if not rel:
            return []
        rows = list(
            rel.values("date", "impressions", "clicks", "spend", "sales", "roas")
        )
        from decimal import Decimal

        for r in rows:
            for k in ("spend", "sales", "roas"):
                v = r.get(k)
                if isinstance(v, Decimal):
                    r[k] = float(v) if v.is_finite() else None
        return rows


class CampaignUpdateIn(Schema):
    name: Optional[str] = None
    objectives: Optional[str] = None
    creative: Optional[Dict[str, Any]] = None
    target: Optional[Dict[str, Any]] = None
    budget: Optional[Dict[str, Any]] = None
    duration: Optional[Dict[str, Any]] = None


class CampaignStatusOut(Schema):
    id: int
    name: str
    status: str
    message: str


class CampaignStatusUpdateIn(Schema):
    status: Campaign.CampaignStatus  # 또는: str
