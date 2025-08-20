# ai_insights/serializers.py
from rest_framework import serializers

from .models import Insight, InsightAnalysisItem, InsightRecommendation, InsightTag


# --- 기존(리스트용) 시리얼라이저들 ---
class ReasonSummarySerializer(serializers.Serializer):
    icon = serializers.CharField()
    text = serializers.CharField()


class InsightTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = InsightTag
        fields = ["text", "type"]


class NewStrategySerializer(serializers.ModelSerializer):
    reason_summary = serializers.SerializerMethodField()
    isNew = serializers.BooleanField(source="is_new")

    class Meta:
        model = Insight
        fields = ["id", "title", "reason_summary", "created_at", "isNew"]

    def get_reason_summary(self, obj):
        return {"icon": obj.reason_icon or "", "text": obj.reason_text or ""}


class RecommendedStrategySerializer(serializers.ModelSerializer):
    tags = InsightTagSerializer(many=True)

    class Meta:
        model = Insight
        fields = ["id", "icon", "title", "tags"]


class InsightDetailSerializer(serializers.ModelSerializer):
    """
    (하위 호환: 예전 1번 포맷)
    """

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


# --- 2번 포맷용(새 상세) 시리얼라이저 ---
class AnalysisItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InsightAnalysisItem
        fields = ["icon", "title", "description"]


class RecommendationSerializer(serializers.ModelSerializer):
    item = serializers.SerializerMethodField()

    class Meta:
        model = InsightRecommendation
        fields = ["title", "item"]

    def get_item(self, obj):
        return {
            "icon": obj.item_icon or "",
            "title": obj.item_title,
            "description": obj.item_description,
        }


class InsightV2DetailSerializer(serializers.ModelSerializer):
    """
    최종 목표 포맷(2번):
    {
      id, tags[{text,type}], title, summary,
      analysis: { title, items: [...] },
      recommendation: { title, item: {...} }
    }
    """

    tags = InsightTagSerializer(many=True)
    analysis = serializers.SerializerMethodField()
    recommendation = serializers.SerializerMethodField()

    class Meta:
        model = Insight
        fields = ["id", "tags", "title", "summary", "analysis", "recommendation"]

    def get_analysis(self, obj: Insight):
        items_qs = obj.analysis_items.all()
        return {
            "title": "AI 분석 근거",
            "items": AnalysisItemSerializer(items_qs, many=True).data,
        }

    def get_recommendation(self, obj: Insight):
        rec = getattr(obj, "recommendation", None)
        if not rec:
            return None
        return RecommendationSerializer(rec).data
