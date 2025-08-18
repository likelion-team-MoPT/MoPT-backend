import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

# Create your models here.


def _gen_public_id() -> str:
    """
    공지용 public id 생성기. 예: ntc_9a1b2c3d
    마이그레이션에서 default=users.models._gen_public_id 로 참조합니다.
    """
    return f"ntc_{uuid.uuid4().hex[:8]}"


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    nickname = models.CharField(max_length=50, blank=True, default="")
    phone_number = models.CharField(max_length=20, blank=True, default="")
    birthdate = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    profile_image_url = models.URLField(blank=True, default="")

    def __str__(self) -> str:
        return f"Profile({self.user_id}, {self.nickname or self.user.username})"


# 현재알림설정값조회


class UserNotificationSetting(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_settings",
    )
    marketing_alerts = models.BooleanField(default=True)
    ai_insights_notification = models.BooleanField(default=True)
    weekly_report_notification = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"NotificationSetting(user={self.user_id})"


# 현재 요금제 조회
class Subscription(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="subscription",
    )
    plan_name = models.CharField(max_length=50)  # 예: "베이직 플랜"
    monthly_price = models.IntegerField()  # 예: 29900 (정수, KRW 기준)
    currency = models.CharField(max_length=8, default="KRW")
    next_payment_date = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Subscription(user={self.user_id}, plan={self.plan_name})"


# 결제카드목록조회
class PaymentMethod(models.Model):

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payment_methods",
    )
    method_id = models.CharField(max_length=64, unique=True)
    card_type = models.CharField(max_length=32)
    last4 = models.CharField(max_length=4)
    is_default = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_default", "-created_at"]

    def __str__(self):
        return f"{self.user_id} - {self.card_type} ****{self.last4}"

    @property
    def masked_number(self) -> str:
        return f"**** **** **** {self.last4}"


# 결제내역조회
class BillingInvoice(models.Model):

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="billing_invoices",
    )
    invoice_id = models.CharField(max_length=64, unique=True)  # 예: "inv-20250715"
    plan_name = models.CharField(max_length=100)  # 예: "베이직 플랜"
    amount = models.IntegerField()  # 예: 29900 (원)
    currency = models.CharField(max_length=8, default="KRW")  # 확장 대비
    paid_at = models.DateTimeField()  # 결제일(UTC)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-paid_at"]

    def __str__(self):
        return f"{self.invoice_id} ({self.user_id})"


# ----공지사항목록조회


class Notice(models.Model):
    public_id = models.CharField(
        max_length=40,
        unique=True,
        default=_gen_public_id,  # <- 마이그레이션과 동일
        db_index=True,
    )
    title = models.CharField(max_length=255)
    body = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.public_id} - {self.title}"
