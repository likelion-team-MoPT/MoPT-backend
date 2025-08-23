from django.db import models


class TrendKeyword(models.Model):
    """
    지역별 상권 트렌드 키워드를 저장하는 테이블.
    - region: 조회할 지역명 (예: '강남구', '마포구' 등 정규화된 행정구 단위로 저장 권장)
    - keyword: 노출할 키워드
    - created_at: 생성시각 (최신순으로 5개까지 노출)
    """

    region = models.CharField(max_length=50, db_index=True)
    keyword = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]  # 최신 생성순
        indexes = [
            models.Index(fields=["region", "-created_at"]),
        ]
        # ✅ (region, keyword) 중복을 원천 차단
        unique_together = (("region", "keyword"),)

    def __str__(self):
        return f"[{self.region}] {self.keyword}"
