from datetime import datetime
from django.http import JsonResponse
from django.utils.dateformat import format as dj_format
from django.views import View

from ai_insights.models import Insight
from home.models import TrendKeyword

class DashboardSummaryView(View):
    """
    홈 대시보드 데이터 조회
    [GET] /api/dashboard?region={string}

    응답:
    {
        "insights": [
            {"id":"insight_001", "title":"...", "created_at":"2025-08-01"},
            ...
        ],
        "count": 3,
        "trend_keywords": ["피크닉 도시락", "혼밥 맛집", "SNS 인기 메뉴", "여름 음료", "가성비 식당"]
    }

    동작:
    - AI 인사이트: 최근 3개 + 전체 개수
    - 상권 트렌드 키워드: region 필수. 최신 생성순 5개 반환
    """
    def get(self, request):
        region = request.GET.get('region')
        if not region:
            return JsonResponse(
                {"error": "region parameter is required"},
                status=400
            )

        # 1) AI 인사이트 요약 (최근 3개)
        insights_qs = Insight.objects.order_by('-created_at')[:3]
        insights = [
            {
                "id": i.id,
                "title": i.title,
                # created_at을 YYYY-MM-DD로 변환
                "created_at": dj_format(i.created_at, 'Y-m-d'),
            }
            for i in insights_qs
        ]
        insight_count = Insight.objects.count()

        # 2) 상권 트렌드 키워드 (지역별 최신 5개)
        keywords = list(
            TrendKeyword.objects
            .filter(region=region)
            .order_by('-created_at')
            .values_list('keyword', flat=True)[:5]
        )

        data = {
            "insights": insights,
            "count": insight_count,
            "trend_keywords": keywords,
        }
        return JsonResponse(data, status=200, json_dumps_params={"ensure_ascii": False})
