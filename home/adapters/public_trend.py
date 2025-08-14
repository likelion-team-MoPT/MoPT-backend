# -*- coding: utf-8 -*-
"""
home/adapters/public_trend.py

공공데이터 어댑터 (TLS1.2 + certifi + curl 폴백 + 페이지 스캔 + ServiceKey 우선)
- 행안부 법정동코드(1741000): '시군구 풀네임' → 하위 동(법정동) 10자리 코드 목록
- 상권정보(sdsc2, B553077): 법정동코드 기준 업종명 빈도 집계 → Top5

핵심 포인트
- ServiceKey/ serviceKey 케이스 차이로 'HTTP ROUTING ERROR'가 날 수 있음 → 대문자 우선, 실패 시 소문자로 자동 재시도
- .env에 인코딩/디코딩 어떤 형태의 키를 넣어도 자동 정규화 (퍼센트 포함 시 한 번만 unquote)
- Windows SSL 이슈 회피: TLS1.2 강제 + certifi 사용, 그래도 실패하면 시스템 curl 폴백
- 응답 포맷 2종(StanReginCd / response.body.items) 모두 지원
- '강남구'만 들어와도 '서울특별시 강남구'로 보정(서울 25구 한정)
"""

from __future__ import annotations

import ssl
import json
import shlex
import logging
import subprocess
from typing import List, Dict, Any, Iterable, Tuple
from urllib.parse import unquote, quote_plus

import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import SSLError, RequestException
from urllib3.util import Retry, ssl_ as urllib3_ssl
from django.conf import settings

# certifi가 있으면 최신 루트 CA 사용
try:
    import certifi
    _CERT_PATH = certifi.where()
except Exception:
    certifi = None
    _CERT_PATH = None

log = logging.getLogger(__name__)

# -------------------------
# 지역명 보정 (서울 25개 구)
# -------------------------
SEOUL_GU = {
    "강남구", "서초구", "송파구", "강동구", "강북구", "노원구", "도봉구", "성북구",
    "동대문구", "중랑구", "광진구", "강서구", "양천구", "구로구", "금천구", "영등포구",
    "동작구", "관악구", "마포구", "서대문구", "은평구", "용산구", "성동구", "중구", "종로구"
}

def _normalize_region_name(region: str) -> str:
    """'강남구' → '서울특별시 강남구' 보정(서울 25개 구만)."""
    region = (region or "").strip()
    if not region:
        return region
    if " " in region:
        return region
    if region in SEOUL_GU:
        return f"서울특별시 {region}"
    return region


# -------------------------
# TLS1.2 강제 어댑터 + 재시도 + 최신 CA
# -------------------------
class TLS12HttpAdapter(HTTPAdapter):
    """TLS 1.2로 강제된 커스텀 HTTPAdapter."""
    def __init__(self, *args, **kwargs):
        retries = kwargs.pop("retries", Retry(
            total=3, backoff_factor=0.3,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset(["GET"]),
        ))
        self._ssl_context = self._build_tls12_context()
        super().__init__(max_retries=retries, *args, **kwargs)

    def _build_tls12_context(self) -> ssl.SSLContext:
        if _CERT_PATH:
            ctx = ssl.create_default_context(cafile=_CERT_PATH)
        else:
            ctx = ssl.create_default_context()
        if hasattr(ssl, "TLSVersion"):
            ctx.minimum_version = ssl.TLSVersion.TLSv1_2
            ctx.maximum_version = ssl.TLSVersion.TLSv1_2
        else:
            ctx.options |= urllib3_ssl.OP_NO_TLSv1_3
        return ctx

    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        if not hasattr(self, "_ssl_context") or self._ssl_context is None:
            self._ssl_context = self._build_tls12_context()
        pool_kwargs["ssl_context"] = self._ssl_context
        return super().init_poolmanager(connections, maxsize, block, **pool_kwargs)

    def proxy_manager_for(self, proxy, **proxy_kwargs):
        if not hasattr(self, "_ssl_context") or self._ssl_context is None:
            self._ssl_context = self._build_tls12_context()
        proxy_kwargs["ssl_context"] = self._ssl_context
        return super().proxy_manager_for(proxy, **proxy_kwargs)


def _session_tls12() -> requests.Session:
    s = requests.Session()
    s.mount("https://", TLS12HttpAdapter())
    s.headers.update({"User-Agent": "mopt-backend/1.0 (+requests)"})
    return s


# -------------------------
# 키 정규화 유틸
# -------------------------
def _normalize_service_key(raw: str) -> str:
    """
    .env에 퍼센트(%)가 포함되어 있으면 인코딩 키로 보고 unquote 한 번만 수행.
    퍼센트가 없으면(=이미 디코딩 형태) 그대로 사용.
    """
    raw = (raw or "").strip()
    if not raw:
        return ""
    return unquote(raw) if "%" in raw else raw


# -------------------------
# curl 폴백 유틸 (Windows 인코딩 대응)
# -------------------------
def _curl_get_json(url: str, params: Dict[str, Any], timeout: float) -> Dict[str, Any] | None:
    """requests 실패 시 시스템 'curl'로 동일 요청 수행."""
    try:
        subprocess.run(["curl", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    except Exception:
        log.error("curl 폴백 실패: 시스템에 curl이 설치되어 있지 않습니다.")
        return None

    cmd: list[str] = ["curl", "-sS", "-G", "--max-time", str(int(timeout)), url,
                      "-H", "Accept: application/json", "-H", "Accept-Charset: utf-8"]
    for k, v in (params or {}).items():
        cmd.extend(["--data-urlencode", f"{k}={v}"])

    try:
        log.warning("requests 실패로 curl 폴백 실행: %s", " ".join(shlex.quote(c) for c in cmd))
        proc = subprocess.run(cmd, capture_output=True, text=False, check=False)
        if proc.returncode != 0:
            err = _safe_decode(proc.stderr)
            log.error("curl 폴백 실패 (returncode=%s): %s", proc.returncode, (err[:200] if err else ""))
            return None

        raw = proc.stdout or b""
        if not raw:
            log.error("curl 폴백: 응답 본문이 비어있습니다.")
            return None

        out = _safe_decode(raw)
        if not out:
            log.error("curl 폴백: 응답 디코딩 실패.")
            return None

        try:
            return json.loads(out)
        except json.JSONDecodeError:
            head = out.strip()[:240]
            log.error("curl 폴백: JSON 파싱 실패. 응답 일부: %s", head)
            return None
    except Exception as e:
        log.error("curl 폴백 실행 중 예외: %s", e)
        return None


def _safe_decode(data: bytes) -> str:
    """바이트 → 문자열 안전 디코딩 (utf-8 → cp949 → euc-kr → latin-1)."""
    for enc in ("utf-8", "cp949", "euc-kr", "latin-1"):
        try:
            return data.decode(enc)
        except Exception:
            continue
    return data.decode("utf-8", errors="ignore")


# -------------------------
# 공통 GET (TLS1.2 세션 + curl 폴백)
# -------------------------
def _get(url: str, params: Dict[str, Any], timeout: float) -> Dict[str, Any]:
    """1) requests(TLS1.2) → 2) 실패 시 curl 폴백."""
    try:
        with _session_tls12() as sess:
            resp = sess.get(url, params=params, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
    except (SSLError, RequestException) as e:
        log.error("requests 호출 실패 → curl 폴백 시도: %s", e)
        data = _curl_get_json(url, params, timeout)
        if data is not None:
            return data
        raise


# -------------------------
# 행안부 응답 파서 (두 포맷 지원)
# -------------------------
def _parse_lawd_items(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """행안부 응답에서 아이템 배열을 공통 포맷으로 추출."""
    if not isinstance(data, dict):
        return []
    if "StanReginCd" in data:
        rows: List[Dict[str, Any]] = []
        for block in data["StanReginCd"]:
            if isinstance(block, dict) and "row" in block and isinstance(block["row"], list):
                rows.extend(block["row"])
        return rows
    return data.get("response", {}).get("body", {}).get("items", []) or []


def _filter_codes_by_name(items: Iterable[Dict[str, Any]], region_full: str) -> List[str]:
    """locatadd_nm에 region_full이 포함된 레코드의 region_cd(10자리) 수집."""
    out: List[str] = []
    for r in items:
        name = str(r.get("locatadd_nm", "") or "")
        code = str(r.get("region_cd", "") or "")
        if len(code) >= 10 and region_full in name:
            out.append(code[:10])
    return list(dict.fromkeys(out))


# -------------------------
# 내부: 행안부 호출 헬퍼 (ServiceKey/ serviceKey 자동 전환)
# -------------------------
def _lawd_call(url: str, base_params: Dict[str, Any], timeout: float) -> Tuple[Dict[str, Any] | None, str]:
    """
    ServiceKey(대문자) → 실패 시 serviceKey(소문자)로 자동 재시도.
    반환: (data, used_key_name)
    """
    # 1차: ServiceKey
    params_upper = {"ServiceKey": base_params.pop("ServiceKey"), **base_params}
    try:
        data = _get(url, params_upper, timeout)
        return data, "ServiceKey"
    except Exception as e:
        # 라우팅 에러/SSL 실패 등 → 소문자로 재시도
        pass

    # 2차: serviceKey
    params_lower = {"serviceKey": params_upper.pop("ServiceKey"), **base_params}
    try:
        data = _get(url, params_lower, timeout)
        return data, "serviceKey"
    except Exception as e:
        return None, ""


# ----------------------------------------------------
# 1) 법정동코드 (행안부 1741000) → 하위 동 코드 목록 조회
# ----------------------------------------------------
def fetch_bjdong_codes_by_sigungu(sigungu_name: str, limit: int = 50) -> List[str]:
    """
    입력: '서울특별시 강남구' (권장) 혹은 '강남구'(서울 구만 자동 보정)
    반환: 하위 동(법정동) 코드 10자리 목록 (최대 limit개)

    1차: locatadd_nm=region_full (ServiceKey 우선)
    2차: 페이지 스캔 (pageNo=1..N)
    """
    region_full = _normalize_region_name(sigungu_name)

    base = "https://apis.data.go.kr/1741000/StanReginCd"
    url = f"{base}/getStanReginCdList"

    # 키 정규화 (퍼센트 포함 → unquote 1회)
    service_key = _normalize_service_key(getattr(settings, "LAWD_API_KEY", ""))

    timeout = float(getattr(settings, "LAWD_API_TIMEOUT", 8.0))

    # ---------- 1) 직접 조회 (ServiceKey/ serviceKey 자동 시도) ----------
    base_params = {
        "ServiceKey": service_key,   # 우선 대문자 키 이름
        "pageNo": 1,
        "numOfRows": 1000,
        "type": "json",
        "locatadd_nm": region_full,
    }
    data, used = _lawd_call(url, base_params.copy(), timeout)
    if data:
        # 데이터 없음?
        if "RESULT" in data and data["RESULT"].get("resultCode") != "INFO-0":
            log.warning("직접 조회: RESULT=%s", data["RESULT"])
        else:
            items = _parse_lawd_items(data)
            codes = _filter_codes_by_name(items, region_full)
            if codes:
                return codes[:limit]
            log.warning("직접 조회 결과 없음 → 플랜B(페이지 스캔) 전환")
    else:
        log.warning("직접 조회 실패 → 플랜B(페이지 스캔) 전환")

    # ---------- 2) 플랜B: 페이지 스캔 ----------
    MAX_PAGES = int(getattr(settings, "LAWD_SCAN_MAX_PAGES", 30))
    PAGE_SIZE = 1000
    found: List[str] = []

    for page in range(1, MAX_PAGES + 1):
        page_params = {
            "ServiceKey": service_key,  # 대문자 우선
            "pageNo": page,
            "numOfRows": PAGE_SIZE,
            "type": "json",
        }
        data, used = _lawd_call(url, page_params.copy(), timeout)
        if not data:
            log.warning("페이지 스캔(%s/%s) 실패", page, MAX_PAGES)
            continue

        items = _parse_lawd_items(data)
        if not items:
            if page > 1:
                break
            continue

        chunk = _filter_codes_by_name(items, region_full)
        if chunk:
            found.extend(chunk)

        if len(found) >= limit:
            break

    return list(dict.fromkeys(found))[:limit]


# -------------------------------------------------------------------
# 2) 상권정보(sdsc2) - 동 코드 기준 업종명 집계 Top5 (빈도 기반)
# -------------------------------------------------------------------
def fetch_keywords_by_bjdong_code(bjdong_code: str, rows: int = 1000) -> List[Dict[str, Any]]:
    """
    입력: 법정동코드(10자리)
    반환: [{"keyword": "커피전문점", "frequency": 123}, ...] (최대 5개)
    """
    base = (getattr(settings, "PUBLIC_API_BASE", None) or "https://apis.data.go.kr/B553077/api/open/sdsc2").rstrip("/")
    url = f"{base}/storeListInDong"

    service_key = _normalize_service_key(getattr(settings, "PUBLIC_API_KEY", ""))
    key_name = getattr(settings, "SDSC_PARAM_KEY_NAME", "key")

    params = {
        "ServiceKey": service_key,  # 대문자 우선
        key_name: bjdong_code,
        "numOfRows": rows,
        "pageNo": 1,
        "type": "json",
    }

    # 상권 API는 보통 대소문자 모두 허용되지만, 통일성을 위해 _get 한 번 실패 시 소문자로 재시도
    try:
        data = _get(url, params, float(getattr(settings, "PUBLIC_API_TIMEOUT", 8.0)))
    except Exception:
        params["serviceKey"] = params.pop("ServiceKey")
        try:
            data = _get(url, params, float(getattr(settings, "PUBLIC_API_TIMEOUT", 8.0)))
        except Exception as e:
            log.error("상권정보 호출 실패(%s): %s", bjdong_code, e)
            return []

    body = (data.get("body") or {}).get("items") \
           or data.get("body") \
           or data.get("matchList") \
           or []

    name_keys = ("indsSclsNm", "indsMclsNm", "indsLclsNm", "category", "serviceName")

    bucket: Dict[str, int] = {}
    for row in body:
        if not isinstance(row, dict):
            continue
        keyword = None
        for k in name_keys:
            val = row.get(k)
            if val:
                keyword = str(val).strip()
                break
        if not keyword:
            continue
        bucket[keyword] = bucket.get(keyword, 0) + 1

    items = [
        {"keyword": k, "frequency": v}
        for k, v in sorted(bucket.items(), key=lambda x: x[1], reverse=True)[:5]
    ]
    return items
