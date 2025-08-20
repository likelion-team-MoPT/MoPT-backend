# ai_insights/models.py
from django.db import models


class InsightTag(models.Model):
    TYPE_CHOICES = (
        ("growth", "growth"),
        ("retention", "retention"),
        ("expansion", "expansion"),
    )
    text = models.CharField(max_length=50)  # 예: '#프로모션'
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)

    def __str__(self):
        return f"{self.text} ({self.type})"


class Insight(models.Model):
    id = models.CharField(max_length=50, primary_key=True)  # 예: 'insight_001'
    title = models.CharField(max_length=255)
    # 예전 포맷 호환용 필드(리스트 응답에서 사용 가능)
    reason_icon = models.CharField(max_length=10, null=True, blank=True)
    reason_text = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # 홈/인사이트 구분용
    icon = models.CharField(max_length=32, default="ICON")
    is_new = models.BooleanField(default=False)

    # 태그 (2번 포맷에서도 사용)
    tags = models.ManyToManyField(InsightTag, related_name="insights", blank=True)

    # 2번 상세 포맷 전용 필드
    summary = models.TextField(null=True, blank=True)  # "상권 주변 ~ 제안합니다."

    def __str__(self):
        return f"[{self.id}] {self.title}"


class InsightAnalysisItem(models.Model):
    """
    2번 포맷의 analysis.items[*]
    """

    insight = models.ForeignKey(
        Insight, on_delete=models.CASCADE, related_name="analysis_items"
    )
    icon = models.CharField(max_length=10, default="")  # 예: '🧾'
    title = models.CharField(max_length=100)  # 예: '매출 데이터'
    description = models.TextField()  # 예: '최근 3주간 ...'
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.insight_id} / {self.title}"


class InsightRecommendation(models.Model):
    """
    2번 포맷의 recommendation 블록 (item은 단일)
    """

    insight = models.OneToOneField(
        Insight, on_delete=models.CASCADE, related_name="recommendation"
    )
    title = models.CharField(max_length=100)  # 예: '추천 실행 계획'
    item_icon = models.CharField(max_length=10, default="")  # 예: '🎯'
    item_title = models.CharField(max_length=200)  # 예: 'SNS 기반 주말 ...'
    item_description = models.TextField()  # 예: '주변 기숙사 반경 ...'

    def __str__(self):
        return f"{self.insight_id} / {self.title}"
