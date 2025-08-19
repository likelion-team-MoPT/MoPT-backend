from datetime import date
from typing import List, Optional

from ninja import Schema
from pydantic import Field

from .models import Campaign


# 공통 응답 메시지 스키마
class MessageOut(Schema):
    message: str


# 캠페in 목록 조회의 페이징 정보 (meta)
class PaginationMeta(Schema):
    page: int
    limit: int
    total: int


# 캠페인 목록 조회의 단일 캠페인 정보 (data 내 객체)
class CampaignListItemOut(Schema):
    id: int
    name: str
    channel: str
    status: str
    roas: float
    spend: int
    start_date: date
    end_date: date


# 캠페인 목록 조회 전체 응답
class CampaignListOut(Schema):
    data: List[CampaignListItemOut]
    meta: PaginationMeta


# 캠페인 상세 조회 응답
class CampaignDetailOut(Schema):
    id: int
    name: str
    status: str
    channel: str
    objectives: str
    performance: dict
    daily_performance: list
    duration: dict = Field(
        ..., alias="duration_info"
    )  # 모델 필드와 다른 이름 사용 시 alias 활용 가능
    creative: dict

    # 모델 필드명을 스키마 필드명으로 변환
    @staticmethod
    def resolve_duration_info(obj: Campaign):
        return {"start": obj.start_date, "end": obj.end_date}


# 캠페인 수정 요청 (Request Body)
class CampaignUpdateIn(Schema):
    name: Optional[str] = None
    objectives: Optional[str] = None
    creative: Optional[dict] = None
    target: Optional[dict] = None
    budget: Optional[dict] = None
    duration: Optional[dict] = None


# 캠페인 상태 변경 응답
class CampaignStatusOut(Schema):
    id: int
    name: str
    status: str
    message: str


# 캠페인 상태 변경 요청 (Request Body)
class CampaignStatusUpdateIn(Schema):
    status: Campaign.CampaignStatus
