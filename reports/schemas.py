from datetime import date
from typing import List, Optional

from ninja import Schema
from pydantic import ConfigDict, Field


# 1. 전체 리포트 조회 스키마
class TotalReportOut(Schema):
    total_spent: int
    total_sales: int
    total_clicks: int
    total_impressions: int
    overall_roas: float


# 2. 기간별 KPI 조회 스키마
class KpiMetrics(Schema):
    spend: List[int]
    sales: List[int]


class KpiReportOut(Schema):
    dates: List[date]
    metrics: KpiMetrics


# 3. 채널별 성과 조회 스키마
class ChannelReportOut(Schema):
    # 새 포맷
    label: str  # lowercased channel label
    roas_pct: float  # 100 * sales / spend

    # 구 포맷(프론트 호환용, 있어도 되고 없어도 됨)
    channel: Optional[str] = None
    roas: Optional[float] = Field(default=None)

    # 공통 수치
    spend: int
    sales: int
    impressions: int
    clicks: int


# 4. 캠페인별 성과 조회 스키마
class CampaignReportOut(Schema):
    model_config = ConfigDict(from_attributes=True)

    # take model.id -> campaign_id
    campaign_id: int = Field(validation_alias="id")
    name: str
    channel: str
    spend: int
    sales: int
    # take model.annotate(calculated_roas=...) -> roas
    roas: float = Field(validation_alias="calculated_roas")
