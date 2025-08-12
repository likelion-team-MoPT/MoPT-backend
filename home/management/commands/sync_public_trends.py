"""
사용 예:
python manage.py sync_public_trends --region 강남구
python manage.py sync_public_trends --region 강남구 --limit 30
python manage.py sync_public_trends --region 강남구 --replace false
"""
from django.core.management.base import BaseCommand
from home.adapters.public_trend import fetch_bjdong_codes_by_sigungu, fetch_keywords_by_bjdong_code
from home.services.trend_sync import upsert_trend_keywords

class Command(BaseCommand):
    help = "공공데이터 API로 상권 트렌드 키워드를 갱신합니다. (시군구 단위)"

    def add_arguments(self, parser):
        parser.add_argument("--region", type=str, required=True, help="시군구명 (예: 강남구)")
        parser.add_argument("--limit", type=int, default=50, help="동코드 최대 개수 (기본 50)")
        parser.add_argument("--replace", type=str, default="true", help="기존 데이터 치환 여부(true/false)")

    def handle(self, *args, **opts):
        region = opts["region"]
        limit = int(opts["limit"])
        replace = (opts["replace"].lower() == "true")

        bjdong_codes = fetch_bjdong_codes_by_sigungu(region, limit=limit)
        if not bjdong_codes:
            self.stdout.write(self.style.WARNING(f"[{region}] 법정동코드 조회 실패/없음"))
            return

        bucket = {}
        for code in bjdong_codes:
            items = fetch_keywords_by_bjdong_code(code)
            for it in items:
                k = it["keyword"]
                bucket[k] = bucket.get(k, 0) + int(it.get("frequency", 1))

        top5 = sorted(bucket.items(), key=lambda x: x[1], reverse=True)[:5]
        payload = [{"keyword": k, "frequency": v} for k, v in top5]
        upserted = upsert_trend_keywords(region, payload, replace=replace)
        self.stdout.write(self.style.SUCCESS(f"[{region}] upserted={upserted}, keywords={payload}"))
