from datetime import timedelta
from typing import Dict, List, Optional
from urllib.parse import urlencode

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils import timezone


def _get_provider_conf(provider: str) -> dict:
    conf = getattr(settings, "INTEGRATIONS_OAUTH", {}).get(provider)
    if not conf or not conf.get("client_id") or not conf.get("auth_base"):
        raise ImproperlyConfigured(f"OAuth config missing for provider='{provider}'")
    return conf


def build_oauth_url(
    provider: str,
    scopes: List[str],
    redirect_uri: str,
    prompt: Optional[str],
    state: str,
) -> str:

    conf = _get_provider_conf(provider)

    params = {
        "client_id": conf["client_id"],
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": ",".join(scopes or []),
        "state": state,
    }
    if prompt == "consent":
        params["auth_type"] = "rerequest"

    return f"{conf['auth_base']}?{urlencode(params)}"


# ---

# 실제 연동 시, 여기서 provider별 토큰 교환/계정 조회 API를 호출하도록 교체


def exchange_code_for_token(
    provider: str, code: str, redirect_uri: Optional[str] = None
) -> Dict:
    """
    더미: code -> access_token 교환
    실제 구현에서는 provider별 토큰 엔드포인트 호출
    """
    return {
        "access_token": f"access_{provider}_{code}",
        "refresh_token": f"refresh_{provider}_{code}",
        "expires_at": timezone.now() + timedelta(days=60),
        "granted_scopes": ["instagram_basic", "ads_management"],  # 예시
    }


def fetch_account_info(provider: str, access_token: str) -> Dict:
    """
    더미: access_token으로 계정 기본 정보 조회
    실제 구현에서는 provider Graph/API 호출
    """
    # 예시 Instagram 비즈니스 계정 정보
    return {
        "id": "17841400000000000",
        "name": "brand_official",
        "handle": "@brand_official",
        "business": True,
    }
