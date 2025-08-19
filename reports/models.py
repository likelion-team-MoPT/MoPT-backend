from django.db import models


class DailyPerformance(models.Model):
    date = models.DateField("날짜")
    campaign = models.ForeignKey(
        "campaigns.Campaign",
        on_delete=models.CASCADE,
        related_name="daily_performances",
    )
    spend = models.PositiveIntegerField("지출액", default=0)
    sales = models.PositiveIntegerField("매출", default=0)
    clicks = models.PositiveIntegerField("클릭 수", default=0)
    impressions = models.PositiveIntegerField("노출 수", default=0)

    class Meta:
        unique_together = ("date", "campaign")

    def __str__(self):
        return f"{self.date} - {self.campaign.name}"
