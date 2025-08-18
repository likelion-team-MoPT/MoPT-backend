from django.contrib import admin

from .models import Integration, PosConnection, PosProvider, Provider


# Register your models here.
@admin.register(Provider)
class ProviderAdmin(admin.ModelAdmin):
    list_display = ("code", "label", "category")
    list_filter = ("category",)
    search_fields = ("code", "label")


@admin.register(PosProvider)
class PosProviderAdmin(admin.ModelAdmin):
    list_display = ("code", "label", "auth", "active", "updated_at")
    list_filter = ("active", "auth")
    search_fields = ("code", "label")
    fields = ("code", "label", "auth", "active")


@admin.register(PosConnection)
class PosConnectionAdmin(admin.ModelAdmin):
    list_display = (
        "public_id",
        "provider",
        "store_external_id",
        "status",
        "connected_at",
    )
    search_fields = ("public_id", "store_external_id", "store_name")
    list_filter = ("status", "provider")
    # 비밀키/자격증명은 읽기전용 또는 표시 제외 권장
    readonly_fields = ("public_id", "connected_at", "last_ping_at", "disconnected_at")
    fields = (
        "public_id",
        "provider",
        "store_external_id",
        "store_name",
        "status",
        "connected_at",
        "last_ping_at",
        "disconnected_at",
    )


# 연동해제
@admin.register(Integration)
class IntegrationAdmin(admin.ModelAdmin):
    list_display = (
        "public_id",
        "user",
        "provider",
        "account_name",
        "account_id",
        "status",
        "connected_at",
        "disconnected_at",
    )
    search_fields = (
        "public_id",
        "account_id",
        "account_name",
        "user__username",
        "user__email",
    )
    list_filter = ("provider", "status")
    readonly_fields = ("public_id", "connected_at", "disconnected_at")
    fieldsets = (
        ("기본", {"fields": ("user", "provider", "public_id", "status")}),
        (
            "계정 정보",
            {
                "fields": (
                    "account_id",
                    "account_name",
                    "account_handle",
                    "account_business",
                )
            },
        ),
        (
            "토큰/권한",
            {
                "fields": (
                    "permissions",
                    "access_token",
                    "refresh_token",
                    "token_expires_at",
                )
            },
        ),
        (
            "타임스탬프",
            {"fields": ("connected_at", "disconnected_at", "disconnect_reason")},
        ),
        ("기타", {"fields": ("extra",)}),
    )
