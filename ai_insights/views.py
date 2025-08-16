from rest_framework import generics, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Insight
from .serializers import InsightDetailSerializer


class CustomPagination(PageNumberPagination):
    # ?limit=10 형태로 페이지 사이즈 조절
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
    def get(self, request):
        insights = Insight.objects.order_by("-created_at")
        paginator = CustomPagination()
        page = paginator.paginate_queryset(insights, request)
        serializer = InsightDetailSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class InsightDetailView(APIView):
    def get(self, request, id=None):
        # 1) path로부터 id 받기 (urls에서 /insights/<str:id> 매핑 시 전달됨)
        insight_id = id

        # 2) path가 없으면 query에서 받기
        if not insight_id:
            insight_id = request.query_params.get("insight_id")

        # 3) 최종적으로도 없으면 400
        if not insight_id:
            return Response(
                {"error": "insight_id is required (path or query)"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 4) 조회
        try:
            insight = Insight.objects.get(id=insight_id)
        except Insight.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        # 5) 직렬화 & 응답
        serializer = InsightDetailSerializer(insight)
        return Response(serializer.data, status=status.HTTP_200_OK)
