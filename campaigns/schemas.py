# campaigns/schemas.py
from datetime import date, datetime
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
    # ORM 객체 허용 (Pydantic v2)
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

    # ---- helpers ----
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
            # JSON 직렬화 안전
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

    # ---- resolvers ----
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
        try:
            # 모델에 실제로 존재하는 필드만 교집합으로 추려서 values() 호출
            model = getattr(rel, "model", None)
            if not model:
                return []
            model_fields = {f.name for f in model._meta.get_fields()}
            wanted = {"date", "impressions", "clicks", "spend", "sales", "roas"}
            use_fields = list(wanted & model_fields)

            if use_fields:
                rows = list(rel.values(*use_fields))
            else:
                # 원하는 필드명이 하나도 없으면 전체 values() 후 sanitize
                rows = list(rel.values())
            rows = CampaignDetailOut._sanitize(rows)
            # 프론트 안전용: 누락 키 기본값 채움
            need = ("date", "impressions", "clicks", "spend", "sales", "roas")
            for r in rows:
                for k in need:
                    r.setdefault(k, None)
            return rows

        except Exception:
            # 어떤 이유로든 실패하면 상세 페이지가 죽지 않도록 빈 배열 반환
            return []


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
