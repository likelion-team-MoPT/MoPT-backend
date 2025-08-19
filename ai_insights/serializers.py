from rest_framework import serializers

from .models import Insight, InsightTag


class ReasonSummarySerializer(serializers.Serializer):
    icon = serializers.CharField()
    text = serializers.CharField()


class InsightTagSerializer(serializers.ModelSerializer):
    """
    기존 전략의 태그: { text: string, type: 'growth'|'retention'|'expansion' }
    """

    class Meta:
        model = InsightTag
        fields = ["text", "type"]


# ===== 신규 전략 응답 포맷 =====
class NewStrategySerializer(serializers.ModelSerializer):
    """
    프론트 요구:
    { id, title, reason_summary:{icon,text}, created_at, isNew }
    """

    reason_summary = serializers.SerializerMethodField()
    isNew = serializers.BooleanField(source="is_new")

    class Meta:
        model = Insight
        fields = ["id", "title", "reason_summary", "created_at", "isNew"]

    def get_reason_summary(self, obj):
        return {"icon": obj.reason_icon or "", "text": obj.reason_text or ""}


# ===== 기존 전략 응답 포맷 =====
class RecommendedStrategySerializer(serializers.ModelSerializer):
    """
    프론트 요구:
    { id, icon, title, tags: [{text, type}] }
    """

    tags = InsightTagSerializer(many=True)

    class Meta:
        model = Insight
        fields = ["id", "icon", "title", "tags"]


# ===== 기존 리스트/상세 (하위 호환이 필요하면 유지) =====
class InsightDetailSerializer(serializers.ModelSerializer):
    reason_summary = serializers.SerializerMethodField()

    class Meta:
        model = Insight
        fields = [
            "id",
            "title",
            "reason_summary",
            "description",
            "created_at",
            "is_new",
        ]

    def get_reason_summary(self, obj):
        return {"icon": obj.reason_icon or "", "text": obj.reason_text or ""}
