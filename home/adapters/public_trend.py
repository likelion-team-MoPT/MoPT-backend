"""
공공데이터 어댑터(완전체)
- Encoding Key(.env) → 내부에서 unquote로 Decoding Key로 변환
- urlencode 직접 사용 X, requests.get(params=...)만 사용 (이중 인코딩 방지)
"""

import logging
from typing import List, Dict
from urllib.parse import unquote  # ⚠ Encoding Key → Decoding Key로 변환에 사용

import requests
from django.conf import settings

log = logging.getLogger(__name__)


def _get(url: str, params: dict, timeout: float) -> dict:
    resp = requests.get(url, params=params, timeout=timeout)
    resp.raise_for_status()
    return resp.json()

def fetch_bjdong_codes_by_sigungu(sigungu_name: str, limit: int = 50) -> list[str]:
    """
    '강남구' 같은 시군구명 → 하위 동(법정동) 코드 리스트(10자리).
    """
    try:
        # 행안부 OpenAPI 베이스(서비스URL): /1741000/StanReginCd
        base = "https://apis.data.go.kr/1741000/StanReginCd"
        url = f"{base}/getStanReginCdList"

        # 🔑 Encoding Key(.env) → Decoding Key로 변환해 전달 (이중 인코딩 방지)
        service_key = unquote(settings.LAWD_API_KEY or "")

        # 강남구 같은 키워드로 필터링; 필요 시 '서울특별시 강남구' 형태로 넘겨도 됨
        params = {
            "ServiceKey": service_key,     # 문서 표기대로 대문자 S 사용
            "pageNo": 1,
            "numOfRows": 1000,
            "type": "json",
            "locatadd_nm": sigungu_name,   # '강남구' 또는 '서울특별시 강남구'
        }

        data = _get(url, params, float(getattr(settings, "LAWD_API_TIMEOUT", 6.0)))

        # 응답 구조: { response: { body: { items: [ { region_cd, locatadd_nm, ... } ] } } }
        items = (
            data.get("response", {})
                .get("body", {})
                .get("items", [])
        )

        # 시군구명 포함 행만 추출 + region_cd(10자리) 수집
        codes = []
        for r in items:
            name = str(r.get("locatadd_nm", ""))  # 지역주소명
            code = str(r.get("region_cd", ""))    # 10자리 지역코드
            if not code or len(code) < 10:
                continue
            # '강남구'가 포함된 동만 취합 (시군구 전역이면 그대로)
            if sigungu_name in name:
                codes.append(code[:10])

        # 중복 제거 + 상한
        codes = list(dict.fromkeys(codes))[:limit]
        return codes

    except Exception as e:
        # 로깅 후 빈 리스트 반환 → 상위에서 폴백 처리
        import logging
        logging.getLogger(__name__).warning("법정동코드 조회 실패(행안부API): %s", e)
        return []

def fetch_keywords_by_bjdong_code(bjdong_code: str, rows: int = 1000) -> List[Dict]:
    """
    소상공인 상가(상권)정보 API (sdsc2) - 동 단위 상가목록 → 업종명 빈도 집계 후 Top5 반환
    """
    try:
        base = settings.PUBLIC_API_BASE.rstrip("/")
        url = f"{base}/storeListInDong"
        key_name = getattr(settings, "SDSC_PARAM_KEY_NAME", "key")

        params = {
            "serviceKey": unquote(settings.PUBLIC_API_KEY or ""),  # 🔑 Encoding → Decoding
            key_name: bjdong_code,
            "numOfRows": rows,
            "pageNo": 1,
            "type": "json",
        }

        data = _get(url, params, float(getattr(settings, "PUBLIC_API_TIMEOUT", 6.0)))

        # 응답 구조 후보
        body = (data.get("body") or {}).get("items") \
               or data.get("body") \
               or data.get("matchList") \
               or []

        # 업종/분류명 후보 필드
        name_keys = ("indsSclsNm", "indsMclsNm", "indsLclsNm", "category", "serviceName")

        bucket: Dict[str, int] = {}
        for row in body:
            keyword = None
            for k in name_keys:
                if k in row and row[k]:
                    keyword = str(row[k]).strip()
                    break
            if not keyword:
                continue
            bucket[keyword] = bucket.get(keyword, 0) + 1

        # 상위 5개 추출
        items = [
            {"keyword": k, "frequency": v}
            for k, v in sorted(bucket.items(), key=lambda x: x[1], reverse=True)[:5]
        ]
        return items

    except Exception as e:
        log.warning("상권정보 조회 실패(%s): %s", bjdong_code, e)
        return []
