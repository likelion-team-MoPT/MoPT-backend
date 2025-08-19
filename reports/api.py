from datetime import date, timedelta
from typing import List, Optional

from django.db.models import Case, DecimalField, F, Sum, Value, When
from django.db.models.functions import Cast, Coalesce
from django.utils import timezone
from ninja import Router

from campaigns.models import Campaign

from .models import DailyPerformance
from .schemas import (
    CampaignReportOut,
    ChannelReportOut,
    KpiMetrics,
    KpiReportOut,
    TotalReportOut,
)

router = Router()


# --- 유틸리티 함수 ---
def parse_date_range(
    period: Optional[str] = None,
    startDate: Optional[date] = None,
    endDate: Optional[date] = None,
):
    """상대적 기간(period) 또는 절대적 기간(startDate, endDate)을 파싱하여 날짜 범위를 반환"""
    if period:
        today = timezone.now().date()
        if period == "최근 7일":
            start = today - timedelta(days=6)
            end = today
        elif period == "이번 달":
            start = today.replace(day=1)
            end = today
        elif period == "지난 달":
            last_month_end = today.replace(day=1) - timedelta(days=1)
            start = last_month_end.replace(day=1)
            end = last_month_end
        else:  # 기본값은 최근 7일
            start = today - timedelta(days=6)
            end = today
        return start, end
    elif startDate and endDate:
        return startDate, endDate
    return None, None


def calculate_roas():
    """ROAS 계산 (분모가 0일 경우 대비)"""
    return Case(
        When(spend=0, then=Value(0)),
        default=(
            Cast(F("sales"), DecimalField()) / Cast(F("spend"), DecimalField()) * 100
        ),
        output_field=DecimalField(),
    )


# --- API 엔드포인트 ---


# 1. 전체 리포트 조회
@router.get("/", response=TotalReportOut)
def get_total_report(
    request,
    period: Optional[str] = None,
    startDate: Optional[date] = None,
    endDate: Optional[date] = None,
):
    start_date, end_date = parse_date_range(period, startDate, endDate)

    # [수정] 겹치는 기간을 조회하도록 필터 로직 변경
    report_data = Campaign.objects.filter(
        start_date__lte=end_date, end_date__gte=start_date
    ).aggregate(
        total_spent=Coalesce(Sum("spend"), 0),
        total_sales=Coalesce(Sum("sales"), 0),
        total_clicks=Coalesce(Sum("clicks"), 0),
        total_impressions=Coalesce(Sum("impressions"), 0),
    )

    overall_roas = 0
    if report_data["total_spent"] > 0:
        overall_roas = (report_data["total_sales"] / report_data["total_spent"]) * 100

    return {
        "total_spent": report_data["total_spent"],
        "total_sales": report_data["total_sales"],
        "total_clicks": report_data["total_clicks"],
        "total_impressions": report_data["total_impressions"],
        "overall_roas": round(overall_roas, 2),
    }


# 2. 기간별 KPI 조회
@router.get("/kpi", response=KpiReportOut)
def get_kpi_report(
    request,
    period: Optional[str] = None,
    startDate: Optional[date] = None,
    endDate: Optional[date] = None,
):
    start_date, end_date = parse_date_range(period, startDate, endDate)

    daily_data = (
        DailyPerformance.objects.filter(date__gte=start_date, date__lte=end_date)
        .values("date")
        .annotate(total_spend=Sum("spend"), total_sales=Sum("sales"))
        .order_by("date")
    )

    dates = [item["date"].strftime("%Y-%m-%d") for item in daily_data]
    spend_metrics = [item["total_spend"] for item in daily_data]
    sales_metrics = [item["total_sales"] for item in daily_data]

    return KpiReportOut(
        dates=dates, metrics=KpiMetrics(spend=spend_metrics, sales=sales_metrics)
    )


# 3. 채널별 성과 조회
@router.get("/channel", response=List[ChannelReportOut])
def get_channel_report(
    request,
    period: Optional[str] = None,
    startDate: Optional[date] = None,
    endDate: Optional[date] = None,
):
    start_date, end_date = parse_date_range(period, startDate, endDate)

    # [수정] 겹치는 기간을 조회하도록 필터 로직 변경
    report_data = (
        Campaign.objects.filter(start_date__lte=end_date, end_date__gte=start_date)
        .values("channel")
        .annotate(spend=Sum("spend"), sales=Sum("sales"), roas=calculate_roas())
        .order_by("-spend")
    )
    return report_data


# 4. 캠페인별 성과 조회
@router.get("/campaign", response=List[CampaignReportOut])
def get_campaign_report(
    request,
    period: Optional[str] = None,
    startDate: Optional[date] = None,
    endDate: Optional[date] = None,
    sort: str = "-roas",
    limit: int = 5,
):
    start_date, end_date = parse_date_range(period, startDate, endDate)

    valid_sort_fields = ["roas", "-roas", "spend", "-spend", "sales", "-sales"]
    sort_key = sort.replace("roas", "calculated_roas")
    if sort_key not in [
        s.replace("roas", "calculated_roas") for s in valid_sort_fields
    ]:
        sort_key = "-calculated_roas"

    # [수정] 겹치는 기간을 조회하도록 필터 로직 변경
    report_data = (
        Campaign.objects.filter(start_date__lte=end_date, end_date__gte=start_date)
        .annotate(calculated_roas=calculate_roas())
        .order_by(sort_key)[:limit]
    )

    return list(report_data)
