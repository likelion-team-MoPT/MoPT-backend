from rest_framework import serializers


class TrendKeywordsResponseSerializer(serializers.Serializer):
    """
    홈 대시보드 트렌드 키워드 응답 시리얼라이저
    - trend_keywords: 문자열 리스트
    """

    trend_keywords = serializers.ListField(
        child=serializers.CharField(), allow_empty=True
    )


class InsightSummaryItemSerializer(serializers.Serializer):
    """
    홈 대시보드 내 AI 인사이트 요약에 쓰이는 간략 아이템
    """

    id = serializers.CharField()
    title = serializers.CharField()
    created_at = serializers.DateField()  # 응답은 YYYY-MM-DD 포맷으로


class DashboardResponseSerializer(serializers.Serializer):
    """
    홈 대시보드 최종 응답
    - insights: 최근 3개 요약
    - count: 전체 인사이트 개수
    - trend_keywords: 지역별 상위 키워드(최대 5개)
    """

    insights = InsightSummaryItemSerializer(many=True)
    count = serializers.IntegerField()
    trend_keywords = serializers.ListField(child=serializers.CharField())
