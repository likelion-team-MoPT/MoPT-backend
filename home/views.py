# home/views.py
from __future__ import annotations

import os
from datetime import datetime, time
from datetime import timezone as dt_timezone
from typing import Any, Dict, List, Optional

import requests
from django.conf import settings
from django.http import JsonResponse
from django.utils.dateformat import format as dj_format
from django.utils.timezone import get_current_timezone
from django.views import View

from ai_insights.models import Insight
from home.models import TrendKeyword


class DashboardSummaryView(View):
    """
    홈 대시보드 데이터 조회
    [GET] /api/dashboard?region={string}&user_id={number}

    응답 예시:
    {
        "insights": [
            {"id":"insight_001", "title":"...", "created_at":"2025-08-01"},
            ...
        ],
        "count": 3,
        "trend_keywords": ["피크닉 도시락", "혼밥 맛집", "SNS 인기 메뉴", "여름 음료", "가성비 식당"],
        "campaigns": [
            {"id": "cmp_001", "name": "점심 세트 프로모션", "roas": 328.1},
            {"id": "cmp_002", "name": "신메뉴 런칭 이벤트", "roas": 145.6}
        ],
        "weekly_sales": [
            {"date": "2025-07-01", "sales": 120000},
            ...
        ],
        "notice": {
            "id": "ntc_20250801",
            "title": "8월 정기 점검 안내",
            "created_at": "2025-08-01T09:00:00+09:00"
        }
    }

    동작:
    - AI 인사이트: 최근 3개 + 전체 개수
    - 상권 트렌드 키워드: region 필수. 최신 생성순 5개 반환
    - 캠페인 요약: 활성 캠페인 상위 1~2개(DB 직조회)  → 이미 구현되어 있다면 유지
    - 주간 매출 동향: 리포트 API 내부 호출 (이미 구현되어 있다면 유지)
    - 최신 공지사항: 공지 목록 API 내부 호출하여 1건만 요약해 붙임
    """

    def get(self, request):
        region = request.GET.get("region")
        if not region:
            return JsonResponse({"error": "region parameter is required"}, status=400)

        # (선택) 공지 조회용 사용자 id 확보: ?user_id= 우선, 없으면 로그인 사용자의 pk
        user_id_param = request.GET.get("user_id")
        user_id: Optional[int] = None
        if user_id_param and user_id_param.isdigit():
            user_id = int(user_id_param)
        elif getattr(request, "user", None) and request.user.is_authenticated:
            # 로그인 사용자가 있으면 그 pk 사용
            user_id = getattr(request.user, "pk", None)

        # 1) AI 인사이트 요약 (최근 3개)
        insights_qs = Insight.objects.order_by("-created_at")[:3]
        insights = [
            {
                "id": i.id,
                "title": i.title,
                # created_at을 YYYY-MM-DD로 변환
                "created_at": dj_format(i.created_at, "Y-m-d"),
            }
            for i in insights_qs
        ]
        insight_count = Insight.objects.count()

        # 2) 상권 트렌드 키워드 (지역별 최신 5개)
        keywords = list(
            TrendKeyword.objects.filter(region=region)
            .order_by("-created_at")
            .values_list("keyword", flat=True)[:5]
        )

        # 3) 캠페인 요약 (DB 직조회 방식 유지)
        campaigns = self._get_active_campaign_summaries()

        # 4) 주간 매출 동향 (이미 구현했다면 호출 유지, 없으면 빈 리스트)
        weekly_sales = self._get_weekly_sales_from_reports()

        # 5) 최신 공지사항 1건 (내부 API 호출)
        notice = self._get_latest_notice(user_id=user_id)

        data = {
            "insights": insights,
            "count": insight_count,
            "trend_keywords": keywords,
            "campaigns": campaigns,
            "weekly_sales": weekly_sales,
            "notice": notice,  # 없으면 {}
        }
        return JsonResponse(data, status=200, json_dumps_params={"ensure_ascii": False})

    # ---------------------------
    # 내부 유틸 (캠페인/매출/공지)
    # ---------------------------

    def _get_active_campaign_summaries(self) -> List[Dict[str, Any]]:
        """
        활성 캠페인 1~2개를 DB에서 요약 조회.
        - 기존 구현을 보존하기 위해 DB 직조회 방식을 유지합니다.
        - 다른 팀의 스키마 변경에 대비해 최소 필드만 사용합니다.
        """
        try:
            from campaigns.models import (  # 지연 import로 순환/마이그레이션 이슈 방지
                Campaign,
            )
        except Exception:
            return []

        qs = (
            Campaign.objects.filter(status="active")
            .order_by("-roas")
            .values("id", "name", "roas")[:2]
        )
        # id 유형이 정수라면 문자열로 캐스팅(응답 예시 형식 맞추기 위함)
        return [
            {
                "id": f"cmp_{row['id']}" if isinstance(row["id"], int) else row["id"],
                "name": row.get("name", ""),
                "roas": float(row["roas"]) if row.get("roas") is not None else None,
            }
            for row in qs
        ]

    def _get_weekly_sales_from_reports(self) -> List[Dict[str, Any]]:
        """
        리포트 도메인의 기간별 KPI 조회 API를 내부 호출하여 최근 7일 매출만 꺼내 요약.
        구현이 아직 없거나 실패하면 빈 리스트를 반환.
        """
        base = getattr(settings, "INTERNAL_API_BASE", None) or os.getenv(
            "INTERNAL_API_BASE", "http://localhost:8000"
        )
        url = f"{base}/api/v1/reports"
        # 최근 7일(오늘 제외/포함 등은 팀 규칙에 맞춰 조정)
        tz = get_current_timezone()
        today = datetime.now(tz=tz).date()
        start = today.replace(day=today.day)  # placeholder: 실제는 today - 6일
        # 간단히 today-6 ~ today로 계산
        from datetime import timedelta

        date_from = (today - timedelta(days=6)).strftime("%Y-%m-%d")
        date_to = today.strftime("%Y-%m-%d")

        try:
            resp = requests.get(
                url, params={"startDate": date_from, "endDate": date_to}, timeout=3.5
            )
            if resp.status_code != 200:
                return []
            payload = resp.json() or {}
            dates = payload.get("dates") or []
            sales = (payload.get("metrics") or {}).get("sales") or []
            if not dates or not sales or len(dates) != len(sales):
                return []
            return [{"date": d, "sales": s} for d, s in zip(dates, sales)]
        except Exception:
            return []

    def _get_latest_notice(self, user_id: Optional[int]) -> Dict[str, Any]:
        """
        공지 목록 API (GET /api/v1/users/{id}/notices)를 내부 호출하여
        최신 공지 1건만 요약 형태로 반환.
        - user_id가 없으면 조회하지 않고 {} 반환
        - API가 YYYY-MM-DD만 줄 경우, 대시보드 요구사항에 맞춰 ISO8601(+09:00)로 변환
        """
        if not user_id:
            return {}

        base = getattr(settings, "INTERNAL_API_BASE", None) or os.getenv(
            "INTERNAL_API_BASE", "http://localhost:8000"
        )
        url = f"{base}/api/v1/users/{user_id}/notices"
        try:
            resp = requests.get(url, params={"page": 1, "limit": 1}, timeout=3.5)
            if resp.status_code != 200:
                return {}
            payload = resp.json() or {}
            items = payload.get("data") or []
            if not items:
                return {}

            raw = items[0]
            created_at = raw.get("created_at", "")

            # created_at이 'YYYY-MM-DD' 형태면 09:00 KST로 ISO8601 변환
            iso_created = self._ensure_iso_kst(created_at)

            return {
                "id": raw.get("id", ""),
                "title": raw.get("title", ""),
                "created_at": iso_created,
            }
        except Exception:
            return {}

    @staticmethod
    def _ensure_iso_kst(date_str: str) -> str:
        """
        'YYYY-MM-DD' 또는 이미 ISO8601 문자열을 받아 ISO8601(+09:00)로 반환.
        - 'YYYY-MM-DD'면 09:00:00+09:00으로 맞춤(요구사항 예시와 동일)
        - 이미 'T'가 포함돼 있으면 그대로 반환(단순 통과)
        """
        if not date_str:
            return ""

        if "T" in date_str:
            # 이미 시간/타임존이 포함되어 있다고 가정
            return date_str

        # YYYY-MM-DD → 09:00:00(+09:00)로 변환
        try:
            d = datetime.strptime(date_str, "%Y-%m-%d").date()
            # 한국시간(+09:00)
            kst = dt_timezone(
                dt_timezone.utc.utcoffset(None)
            )  # placeholder, 아래로 교체
        except ValueError:
            return date_str  # 형식이 다르면 원본 리턴

        # Django의 현재 타임존이 Asia/Seoul로 설정되어 있으니 그것을 사용
        tz = get_current_timezone()
        dt_obj = datetime.combine(d, time(9, 0))  # 09:00 고정
        aware = (
            tz.localize(dt_obj)
            if hasattr(tz, "localize")
            else dt_obj.replace(tzinfo=tz)
        )
        return aware.isoformat()
