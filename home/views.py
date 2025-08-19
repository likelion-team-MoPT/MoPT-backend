from django.http import JsonResponse
from django.utils.dateformat import format as dj_format
from django.views import View

from ai_insights.models import Insight
from home.models import TrendKeyword


def _format_campaign_id(raw):
    """
    응답 예시처럼 문자열 id "cmp_001" 형식으로 맞춰줍니다.
    - 외부에서 온 값이 정수면 cmp_001 처럼 변환
    - 이미 문자열(external_id 등)이면 그대로 반환
    """
    try:
        n = int(raw)
        return f"cmp_{n:03d}"
    except Exception:
        return str(raw)


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
        "trend_keywords": ["피크닉 도시락", "혼밥 맛집", "SNS 인기 메뉴", "여름 음료", "가성비 식당"],
        "campaigns": [
            {"id":"cmp_001", "name":"점심 세트 프로모션", "roas":328.1},
            {"id":"cmp_002", "name":"신메뉴 런칭 이벤트", "roas":145.6}
        ]
    }

    동작:
    - AI 인사이트: 최근 3개 + 전체 개수
    - 상권 트렌드 키워드: region 필수. 최신 생성순 5개 반환
    - 진행 캠페인 요약: 진행중(active) 캠페인 1~2개(id/name/roas) 반환
    """

    def get(self, request):
        region = request.GET.get("region")
        if not region:
            return JsonResponse({"error": "region parameter is required"}, status=400)

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

        # 3) 진행 캠페인 요약 (진행중 active 1~2개)
        #    - campaigns 앱/모델이 미완이거나 필드가 달라도 깨지지 않게 방어합니다.
        campaign_summaries = []
        try:
            from campaigns.models import (  # campaigns 앱이 없으면 except로 넘어감
                Campaign,
            )

            qs = Campaign.objects.filter(status="active")
            # updated_at / start_date가 없어도 동작하도록 정렬을 try/except로 감싸요.
            try:
                qs = qs.order_by("-updated_at", "-start_date", "-id")
            except Exception:
                qs = qs.order_by("-id")

            qs = qs[:2]  # 1~2개만

            for c in qs:
                # id 우선순위: external_id(있으면) -> 내부 id 포맷팅
                if hasattr(c, "external_id") and getattr(c, "external_id"):
                    cid = str(getattr(c, "external_id"))
                else:
                    cid = _format_campaign_id(getattr(c, "id", ""))

                # name/roas 필드가 없을 수 있으므로 getattr로 안전 접근
                name = getattr(c, "name", "") or ""
                roas_val = getattr(c, "roas", 0.0) or 0.0

                # float 캐스팅(문자/Decimal이어도 안전)
                try:
                    roas = float(roas_val)
                except Exception:
                    roas = 0.0

                campaign_summaries.append(
                    {
                        "id": cid,
                        "name": name,
                        "roas": roas,
                    }
                )
        except Exception:
            # campaigns 앱이 아직 준비 전이거나 DB가 비어도 그냥 빈 리스트로 반환
            campaign_summaries = []

        data = {
            "insights": insights,
            "count": insight_count,
            "trend_keywords": keywords,
            "campaigns": campaign_summaries,  # ← 추가된 필드
        }
        return JsonResponse(data, status=200, json_dumps_params={"ensure_ascii": False})
