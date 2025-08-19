from datetime import date
from typing import List

from ninja import Schema
from pydantic import Field


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
    channel: str
    spend: int
    sales: int
    roas: float


# 4. 캠페인별 성과 조회 스키마
class CampaignReportOut(Schema):
    campaign_id: int = Field(..., alias="id")
    name: str
    channel: str
    spend: int
    sales: int
    roas: float = Field(..., alias="calculated_roas")
