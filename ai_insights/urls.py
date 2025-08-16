from django.urls import path

from .views import InsightDetailView, InsightListView

urlpatterns = [
    path("", InsightListView.as_view(), name="insight-list"),
    path("<str:id>", InsightDetailView.as_view(), name="insight-detail-by-path"),
    path("detail", InsightDetailView.as_view(), name="insight-detail-by-query"),
]
