import secrets
import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Q
from django.utils import timezone

# Create your models here.
User = get_user_model()


def _make_public_id(provider_code: str) -> str:
    # 예: integration-fb-1a2b3c4d
    prefix = provider_code[:2] if provider_code else "xx"
    return f"integration-{prefix}-{uuid.uuid4().hex[:8]}"


class Provider(models.Model):
    """
    외부 연동 프로바이더(계정연동/pos 공통)
    """

    code = models.CharField(max_length=50, unique=True)  # ex) "facebook", "instagram"
    label = models.CharField(max_length=100)  # ex) "Facebook"
    scopes = models.JSONField(
        default=list, blank=True
    )  # ex) ["instagram_basic","ads_management"]

    # (옵션) "account" | "pos" 같은 분류가 필요하면 추가
    category = models.CharField(max_length=20, default="account")

    def __str__(self):
        return f"{self.code} ({self.label})"


class Integration(models.Model):
    STATUS_CHOICES = (
        ("active", "active"),
        ("revoked", "revoked"),
        ("disconnected", "disconnected"),
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="integrations"
    )
    provider = models.ForeignKey(Provider, on_delete=models.PROTECT)

    # 계정 정보
    public_id = models.CharField(max_length=64, unique=True, db_index=True, blank=True)
    account_id = models.CharField(max_length=100)
    account_name = models.CharField(max_length=200, blank=True)
    account_handle = models.CharField(max_length=200, blank=True)
    account_business = models.BooleanField(default=False)

    # 권한/토큰
    permissions = models.JSONField(default=list, blank=True)
    access_token = models.TextField(blank=True)
    refresh_token = models.TextField(blank=True)
    token_expires_at = models.DateTimeField(null=True, blank=True)

    # 상태/타임스탬프
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    connected_at = models.DateTimeField(auto_now_add=True)
    disconnected_at = models.DateTimeField(null=True, blank=True)
    disconnect_reason = models.TextField(blank=True)

    extra = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "provider", "account_id"]),
        ]

    def save(self, *args, **kwargs):
        # 새 레코드에 public_id 자동 생성
        if not self.public_id and self.provider_id:
            self.public_id = _make_public_id(self.provider.code)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user_id}:{self.provider.code}:{self.account_id}"


# ---지원벤더조회

##???


# ---연결생성(검증포함)
def gen_public_id():
    # 예: pos_9a1b2c3d
    return f"pos_{secrets.token_hex(4)}"


class PosProvider(models.Model):
    code = models.CharField(max_length=50, unique=True)  # 예: brand_a
    label = models.CharField(max_length=100)  # 예: Brand A POS
    auth = models.CharField(max_length=50, default="api_key")
    active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "pos_providers"

    def __str__(self):
        return f"{self.label} ({self.code})"


class PosConnection(models.Model):
    public_id = models.CharField(
        max_length=50, unique=True, default=gen_public_id, db_index=True
    )
    provider = models.ForeignKey(
        PosProvider, on_delete=models.PROTECT, related_name="connections"
    )
    store_external_id = models.CharField(max_length=100)
    store_name = models.CharField(max_length=200, blank=True, default="")
    credentials = models.JSONField(default=dict)  # 받은 자격증명 원본 저장
    webhook_callback_url = models.URLField(blank=True, default="")
    webhook_signing_secret = models.CharField(max_length=128, blank=True, default="")
    status = models.CharField(
        max_length=20, default="active"
    )  # active | disconnected 등
    connected_at = models.DateTimeField(auto_now_add=True)
    last_ping_at = models.DateTimeField(null=True, blank=True)  # 있어야 함
    last_error = models.TextField(null=True, blank=True)
    disconnected_at = models.DateTimeField(null=True, blank=True)
    reason = models.CharField(max_length=50, blank=True, default="")

    class Meta:
        indexes = [
            models.Index(
                fields=["provider", "store_external_id"], name="pos_prov_store_idx_v2"
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "store_external_id"],
                condition=Q(status="active"),
                name="uniq_active_pos_store_per_provider_v2",
            ),
        ]
