# ai_insights/management/commands/seed_insights.py
# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from ai_insights.models import Insight, InsightTag


class Command(BaseCommand):
    help = "Seed initial AI Insights and Tags (idempotent)."

    def handle(self, *args, **options):
        # ✅ InsightTag는 (name 아님) text, type 필드를 사용합니다.
        growth, _ = InsightTag.objects.get_or_create(text="매출 확대", type="growth")
        retention, _ = InsightTag.objects.get_or_create(
            text="고객 유지", type="retention"
        )
        expansion, _ = InsightTag.objects.get_or_create(
            text="경쟁 분석", type="expansion"
        )

        sample_data = [
            {
                "id": "insight_001",
                "title": "주말 점심 할인 캠페인 제안",
                "reason_icon": "ICON1",
                "reason_text": "최근 3주간 점심 시간대 매출 상승",
                "description": "점심 매출이 전주 대비 35% 증가",
                "tags": [growth],
                "icon": "ICON",
                "is_new": True,
            },
            {
                "id": "insight_002",
                "title": "SNS 광고 예산 확대 필요",
                "reason_icon": "ICON2",
                "reason_text": "SNS 유입 전환율이 평균보다 2배 높음",
                "description": "SNS 광고 확대 권장",
                "tags": [growth, retention],
                "icon": "ICON",
                "is_new": True,
            },
            {
                "id": "insight_003",
                "title": "브런치 세트 프로모션 제안",
                "reason_icon": "ICON3",
                "reason_text": "브런치 키워드 검색량 40% 증가",
                "description": "브런치 세트 출시 권장",
                "tags": [growth],
                "icon": "ICON",
                "is_new": True,
            },
            {
                "id": "insight_004",
                "title": "재방문 고객 혜택 필요",
                "reason_icon": "ICON4",
                "reason_text": "재방문 고객 비중 20% 감소",
                "description": "리텐션 프로모션 필요",
                "tags": [retention],
                "icon": "ICON",
                "is_new": False,
            },
            {
                "id": "insight_005",
                "title": "브랜드 인지도 강화",
                "reason_icon": "ICON5",
                "reason_text": "브랜드 검색량 30% 낮음",
                "description": "브랜드 캠페인 권장",
                "tags": [retention, expansion],
                "icon": "ICON",
                "is_new": False,
            },
            {
                "id": "insight_006",
                "title": "신규 음료 출시 기회",
                "reason_icon": "ICON6",
                "reason_text": "여름 음료 키워드 급증",
                "description": "계절 한정 음료 출시",
                "tags": [growth],
                "icon": "ICON",
                "is_new": False,
            },
            {
                "id": "insight_007",
                "title": "주중 저녁 매출 회복",
                "reason_icon": "ICON7",
                "reason_text": "주중 저녁 매출 2개월 하락",
                "description": "저녁 전용 할인/메뉴 필요",
                "tags": [growth, retention],
                "icon": "ICON",
                "is_new": False,
            },
            {
                "id": "insight_008",
                "title": "경쟁사 가격 인하",
                "reason_icon": "ICON8",
                "reason_text": "경쟁사 3곳 10% 인하",
                "description": "차별화 메시지/구성 필요",
                "tags": [expansion],
                "icon": "ICON",
                "is_new": False,
            },
            {
                "id": "insight_009",
                "title": "고객 리뷰 개선 필요",
                "reason_icon": "ICON9",
                "reason_text": "최근 리뷰 평점 0.3 하락",
                "description": "리뷰 이벤트/서비스 개선",
                "tags": [retention],
                "icon": "ICON",
                "is_new": False,
            },
            {
                "id": "insight_010",
                "title": "테이크아웃 수요 증가",
                "reason_icon": "ICON10",
                "reason_text": "테이크아웃 비중 25% 증가",
                "description": "포장 전용 메뉴 출시",
                "tags": [growth],
                "icon": "ICON",
                "is_new": False,
            },
        ]

        with transaction.atomic():
            created_or_updated = 0
            for row in sample_data:
                ins, _ = Insight.objects.update_or_create(
                    id=row["id"],
                    defaults=dict(
                        title=row["title"],
                        reason_icon=row["reason_icon"],
                        reason_text=row["reason_text"],
                        description=row["description"],
                        created_at=timezone.now(),
                        icon=row.get("icon", "ICON"),
                        is_new=row.get("is_new", False),
                    ),
                )
                ins.tags.set(row["tags"])
                created_or_updated += 1

        self.stdout.write(
            self.style.SUCCESS(f"✅ Seeded {created_or_updated} insights.")
        )
        self.stdout.write(self.style.SUCCESS(f"총 개수: {Insight.objects.count()}"))
        self.stdout.write(
            f"샘플: {list(Insight.objects.values_list('id', flat=True)[:5])}"
        )
