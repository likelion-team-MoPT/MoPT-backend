from django.contrib import admin

from .models import TrendKeyword


@admin.register(TrendKeyword)
class TrendKeywordAdmin(admin.ModelAdmin):
    list_display = ("region", "keyword", "created_at")
    list_filter = ("region",)
    search_fields = ("region", "keyword")
    ordering = ("-created_at",)
