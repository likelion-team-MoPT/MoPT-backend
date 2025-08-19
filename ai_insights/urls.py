from django.urls import path

from .views import InsightDetailAPIView, InsightListView

urlpatterns = [
    path("", InsightListView.as_view(), name="insight-list"),
    path("<str:id>/", InsightDetailAPIView.as_view(), name="insight-detail"),
]
