from rest_framework import serializers
from .models import Insight

class ReasonSummarySerializer(serializers.Serializer):
    icon = serializers.CharField()
    text = serializers.CharField()

class InsightDetailSerializer(serializers.ModelSerializer):
    reason_summary = serializers.SerializerMethodField()

    class Meta:
        model = Insight
        fields = ['id', 'title', 'reason_summary', 'description', 'created_at']

    def get_reason_summary(self, obj):
        return {
            "icon": obj.reason_icon,
            "text": obj.reason_text
        }
