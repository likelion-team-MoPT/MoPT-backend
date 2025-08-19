from django.db import models


class InsightTag(models.Model):
    """
    인사이트(기존 전략)용 태그.
    - text: 화면에 보이는 태그 라벨 (예: '점심 매출 개선', 'SNS 반응 상승')
    - type: 색상/의미 구분용 카테고리 ('growth' | 'retention' | 'expansion')
    """

    TAG_TYPES = (
        ("growth", "Growth"),  # 노란색 - 성과/매출/신규
        ("retention", "Retention"),  # 파란색 - 고객/브랜드/관계
        ("expansion", "Expansion"),  # 빨간색 - 경쟁/위험/분석
    )

    text = models.CharField(max_length=50)
    type = models.CharField(max_length=10, choices=TAG_TYPES)

    def __str__(self):
        return f"{self.text} ({self.type})"


class Insight(models.Model):
    """
    AI 인사이트(전략) 공통 모델
    - '신규 전략'과 '기존 전략'을 is_new 플래그로 구분
    - 기존 전략에서 사용할 별도 icon, tags 필드 추가
    """

    id = models.CharField(max_length=50, primary_key=True)  # 예: 'insight_001'
    title = models.CharField(max_length=255)

    # 리스트 화면의 근거 요약 (신규 전략 카드에서 사용)
    reason_icon = models.CharField(max_length=10, null=True, blank=True)  # 📈 등
    reason_text = models.CharField(max_length=255, null=True, blank=True)

    description = models.TextField(null=True, blank=True)

    # 신규/기존 전략 구분
    is_new = models.BooleanField(default=False)

    # 기존 전략 전용 필드 (디자인 요구사항)
    icon = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        help_text="기존 전략 카드에 노출할 아이콘(예: 📣, 🧩 등)",
    )
    tags = models.ManyToManyField(
        InsightTag,
        blank=True,
        related_name="insights",
        help_text="기존 전략에서 노출할 태그 리스트",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.id}] {self.title}"
