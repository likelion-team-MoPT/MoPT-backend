from django.db import models


class TrendKeyword(models.Model):
    """
    지역별 상권 트렌드 키워드를 저장하는 테이블.
    - region: 조회할 지역명 (예: '강남', '홍대', '모현' 등, 프론트 입력과 동일 포맷로 저장)
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

    def __str__(self):
        return f"[{self.region}] {self.keyword}"
