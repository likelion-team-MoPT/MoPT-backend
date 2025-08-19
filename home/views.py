# home/views.py
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import requests
from django.conf import settings
from django.db.models import Sum
from django.http import JsonResponse
from django.utils.dateformat import format as dj_format
from django.views import View

from ai_insights.models import Insight
from home.models import TrendKeyword

KST = timezone(timedelta(hours=9))

# reports_dailyperformance 테이블을 사용하는 모델을 가져옵니다.
# 보통 reports 앱에 DailyPerformance(또는 DailyPerformanceReport) 같은 모델이 있을 겁니다.
# 모델명이 다를 수 있으니 가장 가능성 높은 이름들을 순차 시도합니다.
DailyPerfModel = None
try:
    from reports.models import (
        DailyPerformance as _DPM,  # db_table='reports_dailyperformance'
    )

    DailyPerfModel = _DPM
except Exception:
    try:
        from reports.models import DailyPerformanceReport as _DPR

        DailyPerfModel = _DPR
    except Exception:
        DailyPerfModel = None


class DashboardSummaryView(View):
    """
    홈 대시보드 데이터 조회 (레거시)
    [GET] /api/dashboard?region={string}&from={yyyy-MM-dd}&to={yyyy-MM-dd}

    응답:
    {
        "insights": [...],
        "count": 3,
        "trend_keywords": [...],
        "campaigns": [...],
        "weekly_sales": [{"date":"YYYY-MM-DD","sales":12345}, ...],
        "notice": {...}
    }
    """

    # ----------------------------
    # 내부 공통: 자기 자신에게 API 호출
    # ----------------------------
    def _safe_get_json(
        self, path: str, params: Optional[Dict[str, Any]] = None, timeout: float = 3.5
    ) -> Tuple[bool, Any]:
        base = "http://localhost:8000"  # 개발 로컬에서만 사용
        url = f"{base}{path}"
        try:
            resp = requests.get(url, params=params or {}, timeout=timeout)
            resp.raise_for_status()
            return True, resp.json()
        except requests.RequestException as e:
            return False, f"request_error: {e}"
        except json.JSONDecodeError:
            return False, "json_decode_error"

    # ----------------------------
    # 캠페인 요약 (진행중 상위 1~2개) — 내부 API 사용
    # ----------------------------
    def _fetch_campaign_summary(self) -> List[Dict[str, Any]]:
        ok, data = self._safe_get_json(
            "/api/v1/campaigns", params={"status": "active", "limit": 2}
        )
        if not ok or not isinstance(data, dict):
            return []

        items = data.get("data") or []
        summary: List[Dict[str, Any]] = []
        for item in items[:2]:
            cid = item.get("id")
            name = item.get("name")
            roas = item.get("roas")
            try:
                roas_num = round(float(roas), 1) if roas is not None else None
            except (TypeError, ValueError):
                roas_num = None

            summary.append(
                {
                    "id": f"cmp_{cid}" if cid is not None else None,
                    "name": name,
                    "roas": roas_num,
                }
            )
        return summary

    # ----------------------------
    # 기간 계산 (최근 7일 기본)
    # ----------------------------
    def _calc_from_to(self, req) -> Tuple[str, str]:
        q_from = req.GET.get("from")
        q_to = req.GET.get("to")
        if q_from and q_to:
            return q_from, q_to

        today = datetime.now(KST).date()
        start = today - timedelta(days=6)  # 총 7일
        return (start.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d"))

    # ----------------------------
    # 주간 매출 동향 - 1) DB 직접 조회(reports_dailyperformance)
    # ----------------------------
    def _fetch_weekly_sales_db(self, req) -> List[Dict[str, Any]]:
        if DailyPerfModel is None:
            return []

        start_str, end_str = self._calc_from_to(req)
        try:
            # 문자열 -> date
            start_d = datetime.strptime(start_str, "%Y-%m-%d").date()
            end_d = datetime.strptime(end_str, "%Y-%m-%d").date()
        except ValueError:
            # 잘못된 포맷이면 비움
            return []

        # 기간 내 모든 날짜 시퀀스 생성
        days: List[date] = []
        cur = start_d
        while cur <= end_d:
            days.append(cur)
            cur += timedelta(days=1)

        # DB에서 일자별 sales 합산
        qs = (
            DailyPerfModel.objects.filter(date__range=[start_d, end_d])
            .values("date")
            .annotate(sales_sum=Sum("sales"))
        )
        by_date = {row["date"]: int(row["sales_sum"] or 0) for row in qs}

        # 누락된 날짜는 0으로 채움, 오름차순 정렬
        rows: List[Dict[str, Any]] = [
            {"date": d.strftime("%Y-%m-%d"), "sales": by_date.get(d, 0)} for d in days
        ]
        return rows[-7:]  # 혹시 길면 마지막 7개만

    # ----------------------------
    # 주간 매출 동향 - 2) 내부 API 폴백(/api/v1/reports)
    # ----------------------------
    def _fetch_weekly_sales_api(self, req) -> List[Dict[str, Any]]:
        start_str, end_str = self._calc_from_to(req)
        ok, data = self._safe_get_json(
            "/api/v1/reports", params={"startDate": start_str, "endDate": end_str}
        )
        if not ok or not isinstance(data, dict):
            return []

        dates = data.get("dates") or []
        metrics = data.get("metrics") or {}
        sales = metrics.get("sales") or []

        rows: List[Dict[str, Any]] = []
        for d, s in zip(dates, sales):
            try:
                s_num = int(s)
            except (TypeError, ValueError):
                continue
            rows.append({"date": d, "sales": s_num})
        return rows[-7:]

    # ----------------------------
    # 최신 공지 1건
    # ----------------------------
    def _fetch_latest_notice(self, req) -> Dict[str, Any]:
        user_id = getattr(getattr(req, "user", None), "id", None) or 1
        ok, data = self._safe_get_json(
            f"/api/v1/users/{user_id}/notices", params={"page": 1, "limit": 1}
        )
        if not ok or not isinstance(data, dict):
            return {}

        items = data.get("data") or []
        if not items:
            return {}

        item = items[0]
        nid = item.get("id")
        title = item.get("title")
        created_at = item.get("created_at")

        created_iso = None
        if isinstance(created_at, str):
            if len(created_at) == 10:
                created_iso = f"{created_at}T09:00:00+09:00"
            else:
                created_iso = created_at

        return {"id": nid, "title": title, "created_at": created_iso}

    # ----------------------------
    # 메인 GET
    # ----------------------------
    def get(self, request):
        region = request.GET.get("region")
        if not region:
            return JsonResponse({"error": "region parameter is required"}, status=400)

        # 1) AI 인사이트 요약
        insights_qs = Insight.objects.order_by("-created_at")[:3]
        insights = [
            {
                "id": i.id,
                "title": i.title,
                "created_at": dj_format(i.created_at, "Y-m-d"),
            }
            for i in insights_qs
        ]
        insight_count = Insight.objects.count()

        # 2) 상권 트렌드 키워드
        keywords = list(
            TrendKeyword.objects.filter(region=region)
            .order_by("-created_at")
            .values_list("keyword", flat=True)[:5]
        )

        # 3) 진행 캠페인 요약
        campaigns = self._fetch_campaign_summary()

        # 4) 주간 매출 동향 — DB 우선, 없으면 API 폴백
        weekly_sales = self._fetch_weekly_sales_db(request)
        if not weekly_sales:
            weekly_sales = self._fetch_weekly_sales_api(request)

        # 5) 최신 공지 1건
        notice = self._fetch_latest_notice(request)

        data = {
            "insights": insights,
            "count": insight_count,
            "trend_keywords": keywords,
            "campaigns": campaigns,
            "weekly_sales": weekly_sales,
            "notice": notice,
        }
        return JsonResponse(data, status=200, json_dumps_params={"ensure_ascii": False})
