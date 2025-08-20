# home/api.py
from typing import List, Optional

from django.db.models import Q
from django.utils import timezone
from ninja import Router, Schema

from .models import HomeTrendKeyword  # app에서 실제 모델 경로에 맞춰 import

router = Router()


class TrendKeywordsSchema(Schema):
    trend_keywords: List[str]


@router.get(
    "/dashboard",
    response=TrendKeywordsSchema,
    tags=["홈"],
    summary="대시보드: 상권 트렌드 키워드",
)
def dashboard(request, region: str, limit: Optional[int] = 5):
    """
    GET /api/v1/home/dashboard?region=강남구&limit=5
    """
    qs = (
        HomeTrendKeyword.objects.filter(region__icontains=region)
        .order_by("-created_at")
        .values_list("keyword", flat=True)[: limit or 5]
    )
    return {"trend_keywords": list(qs)}
