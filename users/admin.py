from django.contrib import admin

# Register your models here.
from .models import (
    BillingInvoice,
    Notice,
    PaymentMethod,
    Subscription,
    UserNotificationSetting,
    UserProfile,
)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "nickname", "phone_number", "birthdate", "updated_at")
    search_fields = ("user__username", "user__email", "nickname", "phone_number")


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "plan_name",
        "monthly_price",
        "currency",
        "next_payment_date",
        "updated_at",
    )
    search_fields = ("user__username", "plan_name")
    list_filter = ("currency",)


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = (
        "method_id",
        "user",
        "card_type",
        "last4",
        "is_default",
        "created_at",
    )
    list_filter = ("card_type", "is_default")
    search_fields = ("method_id", "user__username", "user__email")


@admin.register(BillingInvoice)
class BillingInvoiceAdmin(admin.ModelAdmin):
    list_display = ("invoice_id", "user", "plan_name", "amount", "currency", "paid_at")
    search_fields = ("invoice_id", "user__username", "plan_name")
    list_filter = ("currency",)


# ----공지사항목록조회


@admin.register(Notice)
class NoticeAdmin(admin.ModelAdmin):
    list_display = ("public_id", "title", "created_at")
    search_fields = ("public_id", "title")
    list_filter = ("created_at",)
    ordering = ("-created_at",)


# ---현재알림설정값조회
@admin.register(UserNotificationSetting)
class UserNotificationSettingAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "marketing_alerts",
        "ai_insights_notification",
        "weekly_report_notification",
        "updated_at",
    )
    list_filter = (
        "marketing_alerts",
        "ai_insights_notification",
        "weekly_report_notification",
    )
    search_fields = ("user__username", "user__email")
