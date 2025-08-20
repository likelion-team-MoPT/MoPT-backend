# MoPT_backend/urls_legacy.py
# -------------------------------------------------------------------
# ✅ 기존(레거시) 경로만 보관하는 곳
# - urls.py에서는 이 파일을 /api/ 아래에 include만 함
# - 결과 경로:
#     * /api/insights/   → ai_insights.urls (DRF 레거시)
#     * /api/dashboard/  → home.urls (DRF 레거시)
# -------------------------------------------------------------------
from django.urls import include, path

urlpatterns = [
    path(
        "insights/",
        include(
            ("ai_insights.urls", "ai_insights_legacy"), namespace="ai_insights_legacy"
        ),
    ),
    path("dashboard/", include(("home.urls", "home_legacy"), namespace="home_legacy")),
]
