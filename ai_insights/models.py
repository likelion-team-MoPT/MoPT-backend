from django.db import models

class Insight(models.Model):
    id = models.CharField(max_length=50, primary_key=True)  # 예: 'insight_001'
    title = models.CharField(max_length=255)
    reason_icon = models.CharField(max_length=10)  # 📈 등 아이콘 저장
    reason_text = models.CharField(max_length=255)  # 이유 요약 텍스트
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.id}] {self.title}"
