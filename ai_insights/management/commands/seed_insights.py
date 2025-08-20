from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from ai_insights.models import Insight, InsightTag


class Command(BaseCommand):
    help = "Seed 12+ insights (new & recommended) with tags"

    def handle(self, *args, **options):
        with transaction.atomic():

            # 공통 태그 사전(필요한 만큼 재사용)
            tg_growth, _ = InsightTag.objects.get_or_create(
                text="매출 확대", type="growth"
            )
            tg_retention, _ = InsightTag.objects.get_or_create(
                text="고객 유지", type="retention"
            )
            tg_expansion, _ = InsightTag.objects.get_or_create(
                text="경쟁 분석", type="expansion"
            )

            now = timezone.now()

            # ===== 신규 전략 3건 (is_new=True, reason_* 채움) =====
            new_items = [
                dict(
                    id="insight_001",
                    title="주말 점심 할인 캠페인 제안",
                    reason_icon="ICON1",
                    reason_text="최근 3주간 점심 시간대 매출 상승",
                    description="점심 매출이 전주 대비 35% 증가",
                ),
                dict(
                    id="insight_002",
                    title="SNS 광고 예산 확대 필요",
                    reason_icon="ICON2",
                    reason_text="SNS 유입 전환율이 평균보다 2배 높음",
                    description="SNS 도달/전환 효율 양호",
                ),
                dict(
                    id="insight_003",
                    title="브런치 세트 프로모션 제안",
                    reason_icon="ICON3",
                    reason_text="브런치 키워드 검색량 40% 증가",
                    description="브런치 세트 구성 테스트 권장",
                ),
            ]

            for row in new_items:
                ins, _ = Insight.objects.update_or_create(
                    id=row["id"],
                    defaults=dict(
                        title=row["title"],
                        reason_icon=row["reason_icon"],
                        reason_text=row["reason_text"],
                        description=row["description"],
                        created_at=now,
                        is_new=True,
                        icon="",  # 신규 카드에는 icon 미사용
                    ),
                )
                # 신규 카드에는 태그 없음(요구사항 상)
                ins.tags.clear()

            # ===== 기존 전략 9건 (is_new=False, icon + tags) =====
            recommended_items = [
                dict(
                    id="insight_004",
                    title="재방문 고객 혜택 필요",
                    icon="ICON",
                    tags=[tg_retention],
                ),
                dict(
                    id="insight_005",
                    title="브랜드 인지도 강화",
                    icon="ICON",
                    tags=[tg_retention, tg_expansion],
                ),
                dict(
                    id="insight_006",
                    title="신규 음료 출시 기회",
                    icon="ICON",
                    tags=[tg_growth],
                ),
                dict(
                    id="insight_007",
                    title="주중 저녁 매출 회복",
                    icon="ICON",
                    tags=[tg_growth, tg_retention],
                ),
                dict(
                    id="insight_008",
                    title="경쟁사 가격 인하",
                    icon="ICON",
                    tags=[tg_expansion],
                ),
                dict(
                    id="insight_009",
                    title="고객 리뷰 개선 필요",
                    icon="ICON",
                    tags=[tg_retention],
                ),
                dict(
                    id="insight_010",
                    title="테이크아웃 수요 증가",
                    icon="ICON",
                    tags=[tg_growth],
                ),
                dict(
                    id="insight_011",
                    title="직장인 런치 세트 최적화",
                    icon="ICON",
                    tags=[tg_growth],
                ),
                dict(
                    id="insight_012",
                    title="로열티 프로그램 도입",
                    icon="ICON",
                    tags=[tg_retention, tg_growth],
                ),
            ]

            for row in recommended_items:
                ins, _ = Insight.objects.update_or_create(
                    id=row["id"],
                    defaults=dict(
                        title=row["title"],
                        reason_icon="",  # 기존 카드에는 reason_summary 미사용
                        reason_text="",
                        description="",
                        created_at=now,
                        is_new=False,
                        icon=row.get("icon", "ICON"),
                    ),
                )
                ins.tags.set(row["tags"])

        self.stdout.write(
            self.style.SUCCESS("✅ Seeded 12 insights (3 new + 9 recommended)")
        )
