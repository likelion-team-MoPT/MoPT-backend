# home/management/commands/seed_trend_keywords.py
# 새 파일
from django.core.management.base import BaseCommand

from home.models import TrendKeyword

DATA = {
    "강남": ["혼밥 맛집", "점심 세트", "브런치", "테이크아웃", "여름 음료"],
    "강남구": ["혼밥 맛집", "점심 세트", "브런치", "테이크아웃", "여름 음료"],
    "홍대": ["카공 카페", "감성 인테리어", "디저트", "사진 스팟", "에이드"],
    "모현": ["가성비", "단체석", "가족 외식", "지역 맛집", "신메뉴"],
}


class Command(BaseCommand):
    help = "Seed TrendKeyword for home dashboard (safe to re-run)"

    def handle(self, *args, **options):
        created = 0
        for region, words in DATA.items():
            for kw in words:
                obj, was_created = TrendKeyword.objects.get_or_create(
                    region=region, keyword=kw
                )
                if was_created:
                    created += 1
        self.stdout.write(self.style.SUCCESS(f"Seeded {created} TrendKeyword rows"))
