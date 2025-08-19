from django.urls import path

from .views import InsightDetailAPIView, InsightListView

urlpatterns = [
    path("insights", InsightListView.as_view(), name="insight-list"),
    path("insights/<str:id>", InsightDetailAPIView.as_view(), name="insight-detail"),
]
