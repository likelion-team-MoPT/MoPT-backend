from rest_framework import generics
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Insight
from .serializers import (
    InsightDetailSerializer,
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
      - 기본: 신규(new)와 기존(recommended) 둘 다 묶어서 내려줌
        {
          "new_strategies": [...],
          "recommended_strategies": [...]
        }

    쿼리로 분리 조회도 지원:
      - /api/insights?kind=new           → 신규만
      - /api/insights?kind=recommended   → 기존만
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

        # 기본: 둘 다
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
    (하위 호환용 상세)
    """

    queryset = Insight.objects.all()
    serializer_class = InsightDetailSerializer
    lookup_field = "id"
