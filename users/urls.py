# users/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # 프로필
    path('users/1/profile', views.get_profile),          # GET
    path('users/1/profile', views.update_profile),       # PATCH 
    path('users/1/password', views.change_password),     # PATCH

    # 연동
    path('users/1/integrations', views.get_integrations),                  # GET
    path('users/1/integrations/<str:integration_id>', views.delete_integration),  # DELETE

    # 알림 설정
    path('users/1/settings/notifications', views.get_notifications),       # GET
    path('users/1/settings/notifications', views.update_notifications),    # PUT

    # 결제/구독
    path('users/1/billing/subscription', views.get_subscription),          # GET
    path('users/1/billing/payment-methods', views.get_payment_methods),    # GET
    path('users/1/billing/history', views.get_billing_history),            # GET

    # 공지
    path('users/1/notices', views.get_notices),                            # GET (page/limit)
    path('users/1/notices/<str:notice_id>', views.get_notice_detail),      # GET
]
