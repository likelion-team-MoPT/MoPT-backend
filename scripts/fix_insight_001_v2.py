# -*- coding: utf-8 -*-
from django.db import transaction

from ai_insights.models import (
    Insight,
    InsightAnalysisItem,
    InsightRecommendation,
    InsightTag,
)

INSIGHT_ID = "insight_001"


@transaction.atomic
def run():
    # 1) Insight 본문/요약 세팅
    ins, _ = Insight.objects.update_or_create(
        id=INSIGHT_ID,
        defaults=dict(
            title="주말 점심 할인 캠페인 제안",
            summary="상권 주변 기숙사생들의 주말 점심 소비 패턴을 분석하여 매출 증대를 위한 타겟팅 전략을 제안합니다.",
            is_new=True,
            reason_icon="ICON1",
            reason_text="최근 3주간 점심 시간대 매출 상승",
            description="점심 매출이 전주 대비 35% 증가",
            icon="ICON",
        ),
    )

    # 2) 태그 교체: ['#프로모션'(growth), '#시간대마케팅'(retention)]
    want_tags = [
        ("#프로모션", "growth"),
        ("#시간대마케팅", "retention"),
    ]
    tag_objs = []
    for text, typ in want_tags:
        tag, _ = InsightTag.objects.get_or_create(text=text, type=typ)
        tag_objs.append(tag)
    ins.tags.set(tag_objs)

    # 3) 분석 아이템 전부 갈아끼우기
    ins.analysis_items.all().delete()
    items = [
        (
            "🧾",
            "매출 데이터",
            "최근 3주간 주말 점심 매출이 평균 대비 18% 상승하였습니다.",
        ),
        (
            "📍",
            "시장 데이터",
            "상권 내 기숙사생들의 주말 외식 빈도가 다른 요일 대비 높게 나타났습니다.",
        ),
        (
            "💬",
            "SNS 트렌드",
            "“기숙사”, “점심 메뉴 추천”, “혼밥 맛집” 관련 키워드가 주말 점심 시간대에 SNS에서 급증하였습니다.",
        ),
    ]
    for i, (icon, title, desc) in enumerate(items):
        InsightAnalysisItem.objects.create(
            insight=ins,
            icon=icon,
            title=title,
            description=desc,
            order=i,
        )

    # 4) 추천(단일) 업서트
    InsightRecommendation.objects.update_or_create(
        insight=ins,
        defaults=dict(
            title="추천 실행 계획",
            item_icon="🎯",
            item_title="SNS 기반 주말 점심 타겟팅 프로모션 제안",
            item_description=(
                "주변 기숙사 반경 1.5km 내 타겟 유저에게 배달앱 쿠폰 + SNS 홍보용 메뉴 카드 콘텐츠 조합을 추천합니다.\n"
                "점심 전 타이밍(오전 11시)에 메시지를 발송하여 “혼밥 할인 세트”를 노출하세요!"
            ),
        ),
    )
    print("✅ fixed:", INSIGHT_ID)


run()
