from django.db import models


class Campaign(models.Model):
    class CampaignStatus(models.TextChoices):
        ACTIVE = "active", "진행중"
        # PAUSED = 'paused', '중단'
        ENDED = "ended", "종료"

    # 기본 정보
    name = models.CharField("캠페인 이름", max_length=255)
    status = models.CharField(
        "상태",
        max_length=20,
        choices=CampaignStatus.choices,
        default=CampaignStatus.ACTIVE,
    )
    channel = models.CharField("채널", max_length=50, blank=True)

    # 성과 지표
    spend = models.PositiveIntegerField("총 소진액", default=0)
    sales = models.PositiveIntegerField("총 매출", default=0)
    clicks = models.PositiveIntegerField("클릭 수", default=0)
    impressions = models.PositiveIntegerField("노출 수", default=0)
    roas = models.DecimalField("ROAS", max_digits=10, decimal_places=2, default=0.0)

    # 기간 정보
    start_date = models.DateField("시작일", null=True, blank=True)
    end_date = models.DateField("종료일", null=True, blank=True)

    # 상세 정보 (JSON 형태로 저장)
    objectives = models.TextField("캠페인 목표", blank=True)
    performance = models.JSONField("종합 성과", default=dict, blank=True)
    # daily_performance = models.JSONField("일별 성과", default=list, blank=True)
    creative = models.JSONField("소재 정보", default=dict, blank=True)
    target = models.JSONField("타겟 정보", default=dict, blank=True)
    budget = models.JSONField("예산 정보", default=dict, blank=True)

    created_at = models.DateTimeField("생성일", auto_now_add=True)
    updated_at = models.DateTimeField("수정일", auto_now=True)

    def __str__(self):
        return self.name
