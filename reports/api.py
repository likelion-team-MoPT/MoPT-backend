from datetime import date, timedelta
from typing import List, Optional

from django.db.models import Case, ExpressionWrapper, F, FloatField, Sum, Value, When
from django.db.models.functions import Coalesce, Lower
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


# --- utils ---
def parse_date_range(
    period: Optional[str] = None,
    startDate: Optional[date] = None,
    endDate: Optional[date] = None,
):
    """Parse relative (period) or absolute (startDate/endDate) range."""
    if period:
        p = (period or "").lower()
        today = timezone.now().date()

        if p in ("7d", "last_7d", "최근 7일"):
            return today - timedelta(days=6), today
        if p in ("30d", "last_30d"):
            return today - timedelta(days=29), today
        if p in ("this_month", "이번 달"):
            return today.replace(day=1), today
        if p in ("last_month", "지난 달"):
            last_month_end = today.replace(day=1) - timedelta(days=1)
            return last_month_end.replace(day=1), last_month_end

        # default: last 7 days
        return today - timedelta(days=6), today

    if startDate and endDate:
        return startDate, endDate
    return None, None


def apply_overlap_filter(qs, start_date: Optional[date], end_date: Optional[date]):
    """Apply date-overlap filter only when bounds are provided."""
    if start_date and end_date:
        return qs.filter(start_date__lte=end_date, end_date__gte=start_date)
    if start_date:
        return qs.filter(end_date__gte=start_date)
    if end_date:
        return qs.filter(start_date__lte=end_date)
    return qs


def calculate_roas_from_fields(sales_field: str = "sales", spend_field: str = "spend"):
    """Return a float ROAS (%) expression using provided field names."""
    return Case(
        When(**{f"{spend_field}__lte": 0}, then=Value(0.0)),
        default=ExpressionWrapper(
            Value(100.0) * F(sales_field) / F(spend_field),
            output_field=FloatField(),
        ),
        output_field=FloatField(),
    )


# --- endpoints ---


# 1) total report
@router.get("/", response=TotalReportOut)
def get_total_report(
    request,
    period: Optional[str] = None,
    startDate: Optional[date] = None,
    endDate: Optional[date] = None,
):
    start_date, end_date = parse_date_range(period, startDate, endDate)
    qs = apply_overlap_filter(Campaign.objects.all(), start_date, end_date)

    report_data = qs.aggregate(
        total_spent=Coalesce(Sum("spend"), 0),
        total_sales=Coalesce(Sum("sales"), 0),
        total_clicks=Coalesce(Sum("clicks"), 0),
        total_impressions=Coalesce(Sum("impressions"), 0),
    )

    overall_roas = 0.0
    if report_data["total_spent"] > 0:
        overall_roas = (report_data["total_sales"] / report_data["total_spent"]) * 100.0

    return {
        "total_spent": int(report_data["total_spent"]),
        "total_sales": int(report_data["total_sales"]),
        "total_clicks": int(report_data["total_clicks"]),
        "total_impressions": int(report_data["total_impressions"]),
        "overall_roas": round(overall_roas, 2),
    }


# 2) KPI report
@router.get("/kpi", response=KpiReportOut)
def get_kpi_report(
    request,
    period: Optional[str] = None,
    startDate: Optional[date] = None,
    endDate: Optional[date] = None,
):
    start_date, end_date = parse_date_range(period, startDate, endDate)
    qs = DailyPerformance.objects.all()
    if start_date:
        qs = qs.filter(date__gte=start_date)
    if end_date:
        qs = qs.filter(date__lte=end_date)

    daily_data = (
        qs.values("date")
        .annotate(
            total_spend=Coalesce(Sum("spend"), 0), total_sales=Coalesce(Sum("sales"), 0)
        )
        .order_by("date")
    )

    # return date objects (schema expects List[date])
    dates = [item["date"] for item in daily_data]
    spend_metrics = [int(item["total_spend"]) for item in daily_data]
    sales_metrics = [int(item["total_sales"]) for item in daily_data]

    return KpiReportOut(
        dates=dates, metrics=KpiMetrics(spend=spend_metrics, sales=sales_metrics)
    )


# 3) channel performance
@router.get("/channel", response=List[ChannelReportOut])
def get_channel_report(
    request,
    period: Optional[str] = None,
    startDate: Optional[date] = None,
    endDate: Optional[date] = None,
):
    start_date, end_date = parse_date_range(period, startDate, endDate)

    qs = apply_overlap_filter(
        Campaign.objects.exclude(channel__isnull=True).exclude(channel__exact=""),
        start_date,
        end_date,
    )

    # 1) 채널 라벨(소문자) + 원본 채널 둘 다 붙여서 집계
    agg = (
        qs.annotate(label=Lower("channel"))
        .values("label", "channel")
        .annotate(
            spend=Coalesce(Sum("spend"), 0),
            sales=Coalesce(Sum("sales"), 0),
            impressions=Coalesce(Sum("impressions"), 0),
            clicks=Coalesce(Sum("clicks"), 0),
        )
        .order_by("-sales")
    )

    # 2) ROAS 계산 + 호환 키 동시 제공
    rows = []
    for r in agg:
        spend = float(r.get("spend") or 0)
        sales = float(r.get("sales") or 0)
        roas_pct = 0.0 if spend <= 0 else 100.0 * sales / spend

        rows.append(
            {
                # 새 포맷
                "label": r.get("label") or (r.get("channel") or "").lower(),
                "roas_pct": round(roas_pct, 2),
                # 구 포맷(프론트 호환)
                "channel": r.get("channel"),
                "roas": round(roas_pct, 2),
                # 공통 수치
                "spend": int(spend),
                "sales": int(sales),
                "impressions": int(r.get("impressions") or 0),
                "clicks": int(r.get("clicks") or 0),
            }
        )
    return rows


# 4) campaign performance
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
    qs = apply_overlap_filter(Campaign.objects.all(), start_date, end_date)

    valid_sort_fields = {"roas", "-roas", "spend", "-spend", "sales", "-sales"}
    sort_key = sort.replace("roas", "calculated_roas")
    if sort_key not in {
        s.replace("roas", "calculated_roas") for s in valid_sort_fields
    }:
        sort_key = "-calculated_roas"

    qs = qs.annotate(
        calculated_roas=calculate_roas_from_fields("sales", "spend")
    ).order_by(sort_key)[: max(1, int(limit))]

    return list(qs)
