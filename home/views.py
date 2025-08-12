from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from home.models import TrendKeyword
from ai_insights.models import Insight

@api_view(["GET"])
def dashboard(request):
    """
    홈 - AI 인사이트 요약 (최근 3개)
    GET /api/dashboard
    """
    qs = Insight.objects.order_by("-created_at")[:3]
    insights = [{
        "id": i.id,
        "title": i.title,
        "created_at": (i.created_at.date().isoformat() if hasattr(i.created_at, "date") else str(i.created_at)),
    } for i in qs]
    return Response({"insights": insights, "count": len(insights)}, status=status.HTTP_200_OK)

@api_view(["GET"])
def dashboard_trends(request):
    """
    홈 - 상권 트렌드 키워드 (Top5)
    GET /api/dashboard/trends?region=강남구
    """
    region = request.query_params.get("region")
    if not region:
        return Response({"error": "region parameter is required"}, status=status.HTTP_400_BAD_REQUEST)

    qs = TrendKeyword.objects.filter(region=region).order_by("-frequency", "-updated_at")[:5]
    return Response({"trend_keywords": [r.keyword for r in qs]}, status=status.HTTP_200_OK)
