import secrets
import uuid
from datetime import datetime, timedelta
from datetime import timezone as dt_timezone
from typing import Any, Dict, List, Optional

from django.contrib.auth import get_user_model
from django.utils import timezone
from ninja import Router, Schema
from ninja.errors import HttpError
from ninja.responses import Response
from pydantic import BaseModel

from .models import Integration, PosConnection, PosProvider
from .models import Provider as ProviderModel
from .services import build_oauth_url, exchange_code_for_token, fetch_account_info

router = Router(tags=["Integrations"])


# ---
class ProviderOut(Schema):
    id: str
    label: str
    scopes: List[str]


class ProvidersResponse(Schema):
    providers: List[ProviderOut]


@router.get("/providers", response=ProvidersResponse)
def list_providers(request):
    qs = ProviderModel.objects.all().order_by("code")
    data = [
        ProviderOut(
            id=p.code,  # 명세서의 "id"는 DB의 code를 그대로 사용
            label=p.label,
            scopes=p.scopes or [],
        )
        for p in qs
    ]
    return {"providers": data}


# ---
class OAuthUrlIn(Schema):
    provider: str  # "facebook" | "instagram"
    scopes: List[str]  # ["instagram_basic","ads_management"] ...
    redirect_uri: str
    prompt: Optional[str] = None  # "consent" | null


class OAuthUrlOut(Schema):
    auth_url: str
    state: str


@router.post("/oauth/url", response=OAuthUrlOut)
def issue_oauth_url(request, payload: OAuthUrlIn):
    """
    POST /api/v1/integrations/oauth/url
    body: {provider, scopes, redirect_uri, prompt?}
    resp: {auth_url, state}
    """
    # 1) provider 유효성(DB)
    try:
        provider = ProviderModel.objects.get(code=payload.provider)
    except ProviderModel.DoesNotExist:
        raise HttpError(400, f"Unknown provider: {payload.provider}")

    # 2) 스코프: 요청에 명시된 scopes를 우선, 없으면 DB 기본값
    scopes = payload.scopes or (provider.scopes or [])

    # 3) state 생성(UUID)
    state = str(uuid.uuid4())

    # 4) provider별 OAuth URL 생성
    auth_url = build_oauth_url(
        provider=payload.provider,
        scopes=scopes,
        redirect_uri=payload.redirect_uri,
        prompt=payload.prompt,
        state=state,
    )

    return {"auth_url": auth_url, "state": state}


class AccountOut(Schema):
    id: str
    name: str
    handle: str
    business: bool


class CallbackOut(Schema):
    integration_id: str
    provider: str
    account: AccountOut
    permissions: List[str]
    connected_at: str
    status: str


@router.get("/oauth/callback", response=CallbackOut)
def oauth_callback(request, provider: str, code: str, state: str):
    """
    GET /api/v1/integrations/oauth/callback?provider=instagram&code=XXX&state=YYY
    - provider 유효성 확인
    - code -> access_token 교환 (더미)
    - access_token으로 계정 정보 조회 (더미)
    - Integration upsert (있으면 갱신, 없으면 생성)
    - 명세서 응답 리턴
    """
    # 1) provider 확인
    try:
        p = ProviderModel.objects.get(code=provider)
    except ProviderModel.DoesNotExist:
        raise HttpError(400, f"Unknown provider: {provider}")

    # 2) state 검증 (실서비스: CSRF 방지로 저장/검증 필요)
    if not state:
        raise HttpError(400, "state is required")

    # 3) code -> token 교환 (더미)
    token = exchange_code_for_token(provider, code)
    access_token = token["access_token"]
    refresh_token = token.get("refresh_token") or ""
    expires_at = token.get("expires_at")
    granted_scopes = token.get("granted_scopes", [])

    # 4) 계정 정보 조회 (더미)
    acct = fetch_account_info(provider, access_token)

    # 5) 연동 저장(업서트)
    User = get_user_model()
    # 인증 안 붙인 개발 단계이므로 우선 첫 사용자(or id=1)에 귀속
    user = (
        request.user
        if getattr(request, "user", None) and request.user.is_authenticated
        else User.objects.first()
    )
    if user is None:
        raise HttpError(400, "No user to attach integration. Create a user first.")

    integ, created = Integration.objects.update_or_create(
        user=user,
        provider=p,
        account_id=acct["id"],
        defaults={
            "account_name": acct.get("name", ""),
            "account_handle": acct.get("handle", ""),
            "account_business": bool(acct.get("business")),
            "permissions": granted_scopes,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_expires_at": expires_at,
            "status": "active",
            # connected_at은 처음 생성 시 auto_now_add로, 갱신 시 유지
        },
    )
    ts = integ.connected_at
    if timezone.is_naive(ts):
        ts = timezone.make_aware(ts, timezone=timezone.get_default_timezone())
    connected_at_str = ts.astimezone(dt_timezone.utc).isoformat().replace("+00:00", "Z")

    return {
        "integration_id": integ.public_id,  # 내부 pk 사용(명세 예시는 문자열; 필요시 별도 id 생성)
        "provider": p.code,
        "account": {
            "id": integ.account_id,
            "name": integ.account_name,
            "handle": integ.account_handle,
            "business": integ.account_business,
        },
        "permissions": integ.permissions or [],
        "connected_at": connected_at_str,
        "status": integ.status,
    }


# ---토큰 갱신(만료 대응)
# ---- 공통 ISO UTC(Z) 포맷 헬퍼 ----
def _to_iso_utc_z(dt):
    if not dt:
        return None
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_default_timezone())
    return dt.astimezone(dt_timezone.utc).isoformat().replace("+00:00", "Z")


# ---- Response Schemas ----
class TokenInfoOut(Schema):
    expires_at: Optional[str] = None


class TokenRefreshOut(Schema):
    integration_id: str
    status: str
    token: TokenInfoOut
    message: str


# ---- POST /api/v1/integrations/{integration_id}/refresh ----
@router.post("/{integration_id}/refresh", response=TokenRefreshOut)
def refresh_integration_token(request, integration_id: str):
    """
    토큰 갱신(만료 대응)
    - path: /api/v1/integrations/{integration_id}/refresh
    - integration_id 는 public_id (예: integration-in-08e9b142)
    """
    try:
        integ = Integration.objects.select_related("provider").get(
            public_id=integration_id
        )
    except Integration.DoesNotExist:
        raise HttpError(404, "Integration not found")

    # 비활성/해제 상태면 갱신 불가(정책에 맞게 조정)
    if integ.status != "active":
        return TokenRefreshOut(
            integration_id=integ.public_id,
            status=integ.status,
            token=TokenInfoOut(expires_at=_to_iso_utc_z(integ.token_expires_at)),
            message="Integration is not active.",
        )

    if not integ.refresh_token:
        # 실제 서비스라면 provider refresh 엔드포인트 호출 실패 케이스 등을 매핑
        raise HttpError(400, "No refresh_token stored for this integration.")

    # ---- 더미 갱신 로직 ----
    # 실제 구현에서는 provider API 호출로 새 access_token / 만료시각을 받아와야 함
    now = datetime.now()
    new_expires = now + timedelta(days=60)  # 예시: 60일 연장
    # (옵션) access_token 갱신 더미
    integ.access_token = f"{integ.provider.code}_access_{int(now.timestamp())}"
    integ.token_expires_at = new_expires
    integ.save(update_fields=["access_token", "token_expires_at"])

    return TokenRefreshOut(
        integration_id=integ.public_id,
        status=integ.status,
        token=TokenInfoOut(expires_at=_to_iso_utc_z(integ.token_expires_at)),
        message="Token refreshed.",
    )


# ---지원벤더조회
# ---------- POS Providers ----------
class PosProviderOut(Schema):
    id: str  # code
    label: str
    auth: str


class PosProvidersResponse(Schema):
    providers: List[PosProviderOut]


@router.get("/pos/providers", response=PosProvidersResponse)
def list_pos_providers(request):
    qs = PosProvider.objects.all().order_by("label")
    return {"providers": [{"id": p.code, "label": p.label, "auth": p.auth} for p in qs]}


# ---연결생성(검증포함)
# ====== POS: 연결 생성(검증 포함) ======


# 요청 스키마
class PosStoreIn(Schema):
    external_id: str
    name: Optional[str] = None


class PosWebhookIn(Schema):
    callback_url: Optional[str] = None
    signing_secret: Optional[str] = None  # "auto-generate" 허용


class PosConnectionIn(Schema):
    provider: str  # 예: "brand_a"
    credentials: Dict[str, Any]  # 예: {"api_key": "..."}
    store: PosStoreIn
    webhook: Optional[PosWebhookIn] = None


# 응답 스키마
class PosStoreOut(Schema):
    external_id: str
    name: Optional[str] = None


class PosConnectionOut(Schema):
    connection_id: str
    provider: str
    store: PosStoreOut
    status: str
    connected_at: str


# 내부: 지원 브랜드(seed) — providers 엔드포인트와 맞춤
_POS_BRANDS = {
    "brand_a": "Brand A POS",
    "brand_b": "Brand B POS",
}


def _get_or_seed_pos_provider(code: str) -> PosProvider:
    if code not in _POS_BRANDS:
        raise HttpError(400, f"Unknown POS provider: {code}")
    obj, _ = PosProvider.objects.get_or_create(
        code=code, defaults={"label": _POS_BRANDS[code]}
    )
    return obj


def _verify_pos_credentials(provider: str, credentials: Dict[str, Any]) -> None:
    """
    데모용 간단 검증: api_key 존재 여부만 확인.
    실제로는 provider별 API 호출 등을 넣으면 됨.
    """
    if not isinstance(credentials, dict) or not credentials.get("api_key"):
        raise HttpError(400, "Invalid credentials: 'api_key' is required.")


@router.post("/pos/connections", response={201: PosConnectionOut})
def create_pos_connection(request, payload: PosConnectionIn):
    # 1) 제공 브랜드 확인(없으면 seed)
    provider = _get_or_seed_pos_provider(payload.provider)

    # 2) 자격증명 검증(더미)
    _verify_pos_credentials(provider.code, payload.credentials)

    # 3) 웹훅 비밀키 처리
    callback_url = payload.webhook.callback_url if payload.webhook else ""
    secret_in = payload.webhook.signing_secret if payload.webhook else ""
    if secret_in == "auto-generate":
        signing_secret = secrets.token_urlsafe(32)
    else:
        signing_secret = secret_in or ""

    # 4) 연결 저장
    conn = PosConnection.objects.create(
        provider=provider,
        store_external_id=payload.store.external_id,
        store_name=payload.store.name or "",
        credentials=payload.credentials,
        webhook_callback_url=callback_url or "",
        webhook_signing_secret=signing_secret,
        status="active",
    )

    out = PosConnectionOut(
        connection_id=conn.public_id,
        provider=provider.code,
        store=PosStoreOut(
            external_id=conn.store_external_id, name=conn.store_name or None
        ),
        status=conn.status,
        connected_at=_to_iso_utc_z(conn.connected_at),
    )
    return 201, out


# ---연결 상태/헬스체크


# 헬스체크 응답 스키마
class PosHealthCheckOut(Schema):
    connection_id: str
    status: str
    last_ping_at: Optional[str] = None
    last_error: Optional[str] = None


@router.get("/pos/connections/{connection_id}/health", response=PosHealthCheckOut)
def get_pos_connection_health(request, connection_id: str):
    try:
        conn = PosConnection.objects.get(public_id=connection_id)
    except PosConnection.DoesNotExist:
        raise HttpError(404, "POS connection not found")

    conn.last_ping_at = timezone.now()
    conn.save(update_fields=["last_ping_at"])

    return PosHealthCheckOut(
        connection_id=conn.public_id,
        status=conn.status,
        last_ping_at=_to_iso_utc_z(conn.last_ping_at),
        last_error=getattr(conn, "last_error", None),
    )


# ---연동해제
class PosDisconnectOut(Schema):
    integration_id: str
    provider: str
    account_name: str
    connected_at: str
    status: str
    disconnected_at: str
    reason: str


@router.delete("/pos/connections/{connection_id}", response=PosDisconnectOut)
def disconnect_pos_connection(request, connection_id: str):
    try:
        conn = PosConnection.objects.get(public_id=connection_id)
    except PosConnection.DoesNotExist:
        raise HttpError(404, "POS connection not found")

    # 상태 변경
    conn.status = "disconnected"
    conn.disconnected_at = timezone.now()
    conn.reason = "user_request"
    conn.save(update_fields=["status", "disconnected_at", "reason"])

    return PosDisconnectOut(
        integration_id=conn.public_id,  # (스펙 유지: key 이름이 integration_id)
        provider=conn.provider.label if conn.provider else None,
        account_name=conn.store_name,
        connected_at=_to_iso_utc_z(conn.connected_at),
        status=conn.status,
        disconnected_at=_to_iso_utc_z(conn.disconnected_at),
        reason=conn.reason,
    )
