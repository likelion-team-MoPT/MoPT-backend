from django.db import models

class Insight(models.Model):
    title = models.CharField(max_length=255)
    reason_icon = models.CharField(max_length=10) 
    reason_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
