from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),

    # AI 인사이트 (기존)
    path('api/insights/', include('ai_insights.urls')),

    # 홈 대시보드
    path('api/', include('home.urls')),
]
