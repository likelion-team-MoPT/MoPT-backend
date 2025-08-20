# ai_insights/views.py
from rest_framework import generics
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Insight
from .serializers import InsightDetailSerializer  # 하위호환 (v=1)
from .serializers import InsightV2DetailSerializer  # 신규 상세 (디폴트)
from .serializers import (
    NewStrategySerializer,
    RecommendedStrategySerializer,
)


class CustomPagination(PageNumberPagination):
    page_size_query_param = "limit"

    def get_paginated_response(self, data):
        return Response(
            {
                "data": data,
                "meta": {
                    "page": self.page.number,
                    "limit": self.page.paginator.per_page,
                    "total": self.page.paginator.count,
                },
            }
        )


class InsightListView(APIView):
    """
    GET /api/insights
    - 기본: 신규(new) + 기존(recommended)
    - kind=new         → 신규만
    - kind=recommended → 기존만
    """

    def get(self, request):
        kind = (request.GET.get("kind") or "").lower()

        if kind == "new":
            qs_new = Insight.objects.filter(is_new=True).order_by("-created_at")
            return Response(
                {"new_strategies": NewStrategySerializer(qs_new, many=True).data}
            )

        if kind == "recommended":
            qs_rec = Insight.objects.filter(is_new=False).order_by("-created_at")
            return Response(
                {
                    "recommended_strategies": RecommendedStrategySerializer(
                        qs_rec, many=True
                    ).data
                }
            )

        qs_new = Insight.objects.filter(is_new=True).order_by("-created_at")
        qs_rec = Insight.objects.filter(is_new=False).order_by("-created_at")
        data = {
            "new_strategies": NewStrategySerializer(qs_new, many=True).data,
            "recommended_strategies": RecommendedStrategySerializer(
                qs_rec, many=True
            ).data,
        }
        return Response(data)


class InsightDetailAPIView(generics.RetrieveAPIView):
    """
    GET /api/insights/<id>
    - 기본: v2 상세 포맷(요청 예시의 2번)
    - 쿼리 파라미터로 v=1 주면 예전 포맷으로 응답
      예) /api/insights/insight_001?v=1
    """

    queryset = Insight.objects.all()
    lookup_field = "id"

    def get_serializer_class(self):
        v = (self.request.GET.get("v") or "").strip()
        if v == "1":
            return InsightDetailSerializer
        return InsightV2DetailSerializer
