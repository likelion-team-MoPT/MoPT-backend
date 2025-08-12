from typing import List, Dict
from django.db import transaction
from home.models import TrendKeyword

def upsert_trend_keywords(region: str, items: List[Dict], replace: bool = True) -> int:
    """
    region에 대한 키워드 목록을 DB에 반영.
    - replace=True: 기존 region 데이터 삭제 후 새로 채움(Top-N 스냅샷 유지)
    - replace=False: 기존 frequency에 누적
    """
    if replace:
        TrendKeyword.objects.filter(region=region).delete()

    upserted = 0
    with transaction.atomic():
        for it in items:
            keyword = it["keyword"]
            freq = int(it.get("frequency", 1))
            obj, created = TrendKeyword.objects.get_or_create(
                region=region, keyword=keyword,
                defaults={"frequency": freq, "source": "public"}
            )
            if not created and not replace:
                obj.frequency = obj.frequency + freq
                obj.source = "public"
                obj.save(update_fields=["frequency", "source"])
            upserted += 1
    return upserted
