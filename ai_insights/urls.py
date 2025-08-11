# ai_insights/urls.py
from django.urls import path
from .views import InsightListView

urlpatterns = [
    path('', InsightListView.as_view(), name='insight-list'),
]
