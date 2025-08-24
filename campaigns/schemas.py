from datetime import date
from typing import Any, Dict, List, Optional

from ninja import Schema
from pydantic import ConfigDict, Field

from .models import Campaign


# 공통 응답 메시지 스키마
class MessageOut(Schema):
    message: str


# 캠페인 목록 조회의 페이징 정보 (meta)
class PaginationMeta(Schema):
    page: int
    limit: int
    total: int


# 캠페인 목록 조회의 단일 캠페인 정보 (data 내 객체)
class CampaignListItemOut(Schema):
    # Pydantic v2: ORM 객체 허용
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    channel: Optional[str] = None
    status: Optional[str] = None
    roas: Optional[float] = None  # 모델이 Decimal이면 float로 변환됨
    spend: Optional[float] = None  # int/Decimal 어떤 경우든 None 가능성 대비
    start_date: Optional[date] = None
    end_date: Optional[date] = None


# 캠페인 목록 조회 전체 응답
class CampaignListOut(Schema):
    data: List[CampaignListItemOut]
    meta: PaginationMeta


# 캠페인 상세 조회 응답
class CampaignDetailOut(Schema):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    status: Optional[str] = None
    channel: Optional[str] = None

    # 모델에 없을 수도/NULL일 수도 있음 → Optional + 기본값 제공
    objectives: Optional[str] = None
    performance: Dict[str, Any] = Field(default_factory=dict)
    daily_performance: List[Dict[str, Any]] = Field(default_factory=list)

    # alias 쓰지 말고 필드명을 그대로 쓰고 resolver로 채움
    duration: Dict[str, Optional[date]] = Field(default_factory=dict)

    creative: Dict[str, Any] = Field(default_factory=dict)

    # ---------- Resolvers ----------
    @staticmethod
    def resolve_duration(obj: Campaign) -> Dict[str, Optional[date]]:
        return {
            "start": getattr(obj, "start_date", None),
            "end": getattr(obj, "end_date", None),
        }

    @staticmethod
    def resolve_performance(obj: Campaign) -> Dict[str, Any]:
        # 모델에 'performance' JSONField가 실제로 있으면 그대로, 없으면 기본값
        val = getattr(obj, "performance", None)
        return val or {}

    @staticmethod
    def resolve_creative(obj: Campaign) -> Dict[str, Any]:
        val = getattr(obj, "creative", None)
        return val or {}

    @staticmethod
    def resolve_daily_performance(obj: Campaign) -> List[Dict[str, Any]]:
        # 모델에 related name이 daily_performances 라고 보였음 (없으면 빈 리스트)
        rel = getattr(obj, "daily_performances", None)
        if not rel:
            return []
        try:
            return list(
                rel.values("date", "impressions", "clicks", "spend", "sales", "roas")
            )
        except Exception:
            return []


# 캠페인 수정 요청 (Request Body)
class CampaignUpdateIn(Schema):
    name: Optional[str] = None
    objectives: Optional[str] = None
    creative: Optional[Dict[str, Any]] = None
    target: Optional[Dict[str, Any]] = None
    budget: Optional[Dict[str, Any]] = None
    duration: Optional[Dict[str, Any]] = None


# 캠페인 상태 변경 응답
class CampaignStatusOut(Schema):
    id: int
    name: str
    status: str
    message: str


# 캠페인 상태 변경 요청 (Request Body)
class CampaignStatusUpdateIn(Schema):
    # Django Choices Enum을 직접 쓰는 대신 문자열로 받아도 무방합니다.
    # 프로젝트에서 Campaign.CampaignStatus를 잘 쓰고 있으면 그대로 두셔도 되고요.
    status: Campaign.CampaignStatus  # 또는: status: str
