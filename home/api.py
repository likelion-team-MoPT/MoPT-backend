from typing import List, Optional

from django.db.models import Q
from ninja import Router, Schema

from .models import TrendKeyword  # ✅ 올바른 모델 import

router = Router()


class TrendKeywordsSchema(Schema):
    trend_keywords: List[str]


# ✅ 간단한 별칭 매핑 테이블
# - 들어온 region 문자열을 정규화된 지역명으로 보정
REGION_ALIASES = {
    "강남": "강남구",
    "강북": "강북구",
    "마포": "마포구",
    # 필요시 계속 추가
}


def normalize_region(q: str) -> str:
    """
    프론트가 '강남'처럼 축약/별칭을 보내도
    DB는 '강남구' 같은 정규형으로 찾을 수 있도록 보정.
    """
    if not q:
        return q
    q = q.strip()
    return REGION_ALIASES.get(q, q)  # 매핑 없으면 원본 유지


@router.get(
    "/dashboard",
    response=TrendKeywordsSchema,
    tags=["홈"],
    summary="대시보드: 상권 트렌드 키워드",
)
def dashboard(request, region: str, limit: Optional[int] = 5):
    """
    GET /api/v1/home/dashboard?region=강남&limit=5
    - region을 정규화(예: '강남' -> '강남구')한 뒤 정확/부분 일치로 조회
    - 중복 방지를 위해 distinct() 적용
    """
    region_norm = normalize_region(region)

    qs = (
        TrendKeyword.objects.filter(
            Q(region__icontains=region_norm) | Q(region__icontains=region)
        )
        .order_by("-created_at")
        .values_list("keyword", flat=True)
        .distinct()  # ✅ 중복 키워드 방지
    )[: limit or 5]

    return {"trend_keywords": list(qs)}
