from datetime import timezone as dt_timezone
from typing import Any, Dict, List, Optional

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Query, Router, Schema
from ninja.errors import HttpError
from pydantic import BaseModel

from integrations.models import Integration  # 모델은 integrations에서 import

from .models import (
    BillingInvoice,
    Notice,
    PaymentMethod,
    Subscription,
    UserNotificationSetting,
    UserProfile,
)

router = users_router = Router(tags=["Users"])  # 이미 있는 users_router 재사용


class AccountListOut(Schema):
    id: str
    name: Optional[str] = None
    handle: Optional[str] = None
    avatar_url: Optional[str] = None


class IntegrationListItemOut(Schema):
    integration_id: str
    provider: str
    provider_label: str
    account: AccountListOut
    permissions: List[str]
    connected_at: str
    status: str


class IntegrationListResponse(Schema):
    data: List[IntegrationListItemOut]


def _to_iso_utc_z(dt):
    if not dt:
        return None
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_default_timezone())
    return dt.astimezone(dt_timezone.utc).isoformat().replace("+00:00", "Z")


@users_router.get("/{user_id}/integrations", response=IntegrationListResponse)
def list_user_integrations(request, user_id: int):
    qs = (
        Integration.objects.select_related("provider")
        .filter(user_id=user_id)
        .order_by("-connected_at")
    )

    items: List[Dict[str, Any]] = []
    for integ in qs:
        items.append(
            {
                "integration_id": integ.public_id,
                "provider": integ.provider.code,
                "provider_label": integ.provider.label,
                "account": {
                    "id": integ.account_id,
                    "name": integ.account_name or None,
                    "handle": integ.account_handle or None,
                    "avatar_url": (integ.extra or {}).get("avatar_url"),
                },
                "permissions": integ.permissions or [],
                "connected_at": _to_iso_utc_z(integ.connected_at),
                "status": integ.status,
            }
        )

    return {"data": items}


# ---연동해제
# ----- Response Schema -----
class IntegrationDisconnectedOut(Schema):
    integration_id: str
    provider: str
    account_name: str
    connected_at: str
    status: str
    disconnected_at: str
    reason: str


# ----- DELETE API -----
@router.delete(
    "/{user_id}/integrations/{integration_id}",
    response=List[IntegrationDisconnectedOut],
)
def disconnect_user_integration(request, user_id: int, integration_id: str):
    # 1. 해당 유저 & integration_id 조회
    try:
        integ = Integration.objects.select_related("provider").get(
            user_id=user_id, public_id=integration_id
        )
    except Integration.DoesNotExist:
        return []  # 없으면 빈 배열 반환

    # 2. 상태 변경
    integ.status = "disconnected"
    integ.disconnected_at = timezone.now()
    if not getattr(integ, "disconnect_reason", None):
        integ.disconnect_reason = "user_request"
    integ.save(update_fields=["status", "disconnected_at", "disconnect_reason"])

    # 해제된 목록 반환
    qs = (
        Integration.objects.select_related("provider")
        .filter(user_id=user_id, status="disconnected")
        .order_by("-disconnected_at")
    )

    out: List[IntegrationDisconnectedOut] = []
    for i in qs:
        out.append(
            IntegrationDisconnectedOut(
                integration_id=i.public_id,
                provider=i.provider.code,
                account_name=i.account_name or "",
                connected_at=_to_iso_utc_z(i.connected_at),
                status=i.status,
                disconnected_at=_to_iso_utc_z(i.disconnected_at),
                reason=i.disconnect_reason or "user_request",  # 응답 키는 'reason'
            )
        )
    return out


# ---상세프로필조회
class UserProfileOut(Schema):
    nickname: str
    email: str
    phone_number: str
    birthdate: Optional[str]  # "YYYY-MM-DD" or null


@router.get("/{user_id}/profile", response=UserProfileOut)
def get_user_profile(request, user_id: int):
    """
    상세 프로필 조회
    GET /api/v1/users/{user_id}/profile
    """
    User = get_user_model()
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        raise HttpError(404, "User not found")

    # 프로필이 없으면 자동 생성(DB에서 가져오되 없으면 기본값)
    profile, _ = UserProfile.objects.get_or_create(user=user)

    return UserProfileOut(
        nickname=profile.nickname or user.get_username(),
        email=user.email or "",
        phone_number=profile.phone_number or "",
        birthdate=profile.birthdate.isoformat() if profile.birthdate else None,
    )


# 프로필수정
class UserProfileUpdateIn(Schema):
    nickname: Optional[str] = None
    profileImage: Optional[str] = None  # 이미지 URL


class UserProfileFullOut(Schema):
    nickname: str
    email: str
    phone_number: str
    profileImage: Optional[str] = None
    birthdate: Optional[str] = None  # "YYYY-MM-DD" or null


@router.patch("/{user_id}/profile", response=UserProfileFullOut)
def update_user_profile(request, user_id: int, payload: UserProfileUpdateIn):
    """
    프로필 수정
    PATCH /api/v1/users/{user_id}/profile
    body: { nickname?, profileImage? }
    """
    User = get_user_model()
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        raise HttpError(404, "User not found")

    profile, _ = UserProfile.objects.get_or_create(user=user)

    # 변경 파트 (값이 전달된 항목만 업데이트)
    if payload.nickname is not None:
        profile.nickname = payload.nickname
    if payload.profileImage is not None:
        # 필드명이 다르면 여기를 맞춰주세요. (예: profile_image, avatar_url 등)
        profile.profile_image_url = payload.profileImage

    profile.save()

    return UserProfileFullOut(
        nickname=profile.nickname or user.get_username(),
        email=user.email or "",
        phone_number=profile.phone_number or "",
        profileImage=getattr(profile, "profile_image_url", None),
        birthdate=profile.birthdate.isoformat() if profile.birthdate else None,
    )


# --현재알림설정값조회
# --- 현재 알림 설정값 조회


class NotificationSettingsIn(Schema):
    marketing_alerts: bool
    ai_insights_notification: bool
    weekly_report_notification: bool


class NotificationSettingsOut(Schema):
    marketing_alerts: bool
    ai_insights_notification: bool
    weekly_report_notification: bool


# --- 현재 알림 설정값 조회 (GET) ---
@router.get("/{user_id}/settings/notifications", response=NotificationSettingsOut)
def get_notification_settings(request, user_id: int):
    User = get_user_model()
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        raise HttpError(404, "User not found")

    settings, _ = UserNotificationSetting.objects.get_or_create(user=user)
    return NotificationSettingsOut(
        marketing_alerts=settings.marketing_alerts,
        ai_insights_notification=settings.ai_insights_notification,
        weekly_report_notification=settings.weekly_report_notification,
    )


# --- 알림 설정값 수정 (PUT) ---
@router.put("/{user_id}/settings/notifications", response=NotificationSettingsOut)
def update_notification_settings(
    request, user_id: int, payload: NotificationSettingsIn
):
    User = get_user_model()
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        raise HttpError(404, "User not found")

    settings, _ = UserNotificationSetting.objects.get_or_create(user=user)
    settings.marketing_alerts = payload.marketing_alerts
    settings.ai_insights_notification = payload.ai_insights_notification
    settings.weekly_report_notification = payload.weekly_report_notification
    settings.save()

    return NotificationSettingsOut(
        marketing_alerts=settings.marketing_alerts,
        ai_insights_notification=settings.ai_insights_notification,
        weekly_report_notification=settings.weekly_report_notification,
    )


# ---현재 요금제 조회
class SubscriptionOut(Schema):
    plan_name: str
    monthly_price: int
    currency: str
    next_payment_date: Optional[str]


@router.get("/{user_id}/billing/subscription", response=SubscriptionOut)
def get_subscription(request, user_id: int):
    User = get_user_model()
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        raise HttpError(404, "User not found")

    try:
        sub = Subscription.objects.get(user=user)
    except Subscription.DoesNotExist:
        raise HttpError(404, "Subscription not found")

    return SubscriptionOut(
        plan_name=sub.plan_name,
        monthly_price=sub.monthly_price,
        currency=sub.currency,
        next_payment_date=(
            sub.next_payment_date.isoformat() if sub.next_payment_date else None
        ),
    )


# 결제수단
class PaymentMethodOut(Schema):
    method_id: str
    card_type: str
    masked_number: str
    is_default: bool


# --- 결제 카드 목록 조회 ---
@router.get("/{user_id}/billing/payment-methods", response=List[PaymentMethodOut])
def list_payment_methods(request, user_id: int):

    User = get_user_model()
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        raise HttpError(404, "User not found")

    methods = PaymentMethod.objects.filter(user=user).order_by(
        "-is_default", "-created_at"
    )

    return [
        PaymentMethodOut(
            method_id=m.method_id,
            card_type=m.card_type,
            masked_number=m.masked_number,  # 모델의 @property 사용
            is_default=m.is_default,
        )
        for m in methods
    ]


class BillingHistoryItem(Schema):
    invoice_id: str
    payment_date: str  # "YYYY-MM-DD"
    amount: int
    plan_name: str


@router.get("/{user_id}/billing/history", response=List[BillingHistoryItem])
def get_billing_history(request, user_id: int):
    """
    결제 내역 조회
    GET /api/v1/users/{user_id}/billing/history
    """
    User = get_user_model()
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        raise HttpError(404, "User not found")

    invoices = BillingInvoice.objects.filter(user=user).order_by("-paid_at")

    # 명세서 형식: payment_date는 "YYYY-MM-DD"
    return [
        BillingHistoryItem(
            invoice_id=inv.invoice_id,
            payment_date=inv.paid_at.date().isoformat(),
            amount=inv.amount,
            plan_name=inv.plan_name,
        )
        for inv in invoices
    ]


# 공지사항목록조회
# --- Schemas ---
class NoticeItemOut(Schema):
    id: str  # public_id
    title: str
    created_at: str  # "YYYY-MM-DD"


class NoticeListMeta(Schema):
    page: int
    limit: int
    total: int


class NoticeListOut(Schema):
    data: List[NoticeItemOut]
    meta: NoticeListMeta


@router.get("/{user_id}/notices", response=NoticeListOut)
def list_user_notices(request, user_id: int, page: int = 1, limit: int = 6):
    """
    GET /api/v1/users/{user_id}/notices?page=1&limit=6
    - page 기본 1, limit 기본 6
    - 활성 공지만(created_at 내림차순)
    """
    if page < 1:
        page = 1
    if limit < 1:
        limit = 6

    qs = Notice.objects.all().order_by("-created_at")

    total = qs.count()
    start = (page - 1) * limit
    end = start + limit
    slice_qs = qs[start:end]

    items = [
        NoticeItemOut(
            id=n.public_id,  # 명세서의 id
            title=n.title,
            created_at=n.created_at.date().isoformat(),  # YYYY-MM-DD
        )
        for n in slice_qs
    ]

    return NoticeListOut(
        data=items,
        meta=NoticeListMeta(page=page, limit=limit, total=total),
    )


# --------공지사항 세부목록 조회
from ninja import Schema
from ninja.errors import HttpError


class NoticeDetailOut(Schema):
    id: str  # public_id (e.g., "ntc_20250801")
    title: str
    content: str  # body
    created_at: str  # ISO8601 (예: "2025-08-01T09:00:00+09:00")


@router.get("/{user_id}/notices/{notice_id}", response=NoticeDetailOut)
def get_notice_detail(request, user_id: int, notice_id: str):
    """
    공지사항 세부 목록 조회
    GET /api/v1/users/{user_id}/notices/{notice_id}
    - notice_id 는 Notice.public_id
    """
    # (선택) 유저 존재 확인 — 없으면 404
    User = get_user_model()
    if not User.objects.filter(id=user_id).exists():
        raise HttpError(404, "User not found")

    # 공지 조회
    try:
        n = Notice.objects.get(public_id=notice_id)
    except Notice.DoesNotExist:
        raise HttpError(404, "Notice not found")

    created = timezone.localtime(n.created_at).isoformat()

    return NoticeDetailOut(
        id=n.public_id,
        title=n.title,
        content=n.body or "",
        created_at=created,
    )
