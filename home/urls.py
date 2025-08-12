from django.urls import path
from . import views

urlpatterns = [
    path('dashboard', views.dashboard, name='dashboard'),
    path('dashboard/trends', views.dashboard_trends, name='dashboard-trends'),
]
