from django.db import models

class TrendKeyword(models.Model):
    """
    상권 트렌드 키워드 저장 모델
    - region: 시군구명 (예: '강남구')
    - keyword: 키워드 텍스트 (업종/품목명 등)
    - frequency: 빈도값
    - source: 'public' | 'mock' 등
    - updated_at: 갱신 시각(자동)
    """
    region = models.CharField(max_length=50, db_index=True)
    keyword = models.CharField(max_length=100)
    frequency = models.IntegerField(default=1)
    source = models.CharField(max_length=20, default="public")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("region", "keyword")

    def __str__(self):
        return f"[{self.region}] {self.keyword} ({self.frequency})"
