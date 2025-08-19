# MoPT_backend/urls_legacy.py
# -------------------------------------------------------------------
# ✅ 기존(레거시) 경로만 보관하는 곳
# - urls.py에서는 이 파일을 /api/ 아래에 include만 함
# - 결과 경로:
#     * /api/insights/  → ai_insights.urls
#     * /api/           → home.urls
# -------------------------------------------------------------------
from django.urls import include, path

urlpatterns = [
    # AI 인사이트 (기존)
    path("", include("ai_insights.urls")),
    # 홈 대시보드 (기존)
    path("", include("home.urls")),
]
