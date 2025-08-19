from django.urls import path

from .views import DashboardSummaryView

urlpatterns = [
    # 홈 대시보드
    path("", DashboardSummaryView.as_view(), name="dashboard"),
]
