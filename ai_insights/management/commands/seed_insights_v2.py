from django.core.management.base import BaseCommand
from django.db import transaction

from ai_insights.models import (
    Insight,
    InsightAnalysisItem,
    InsightRecommendation,
    InsightTag,
)


def upsert_insight_full(
    *,
    iid: str,
    title: str,
    summary: str,
    tags: list[tuple[str, str]],  # [("#프로모션","growth"), ...]
    analysis_items: list[tuple[str, str, str]],  # [(icon,title,desc), ...]
    rec_title: str,
    rec_item_icon: str,
    rec_item_title: str,
    rec_item_desc: str,
    is_new=False,
):
    # ✅ reason_icon/reason_text를 빈 문자열로 덮어쓰지 않도록 제외
    ins, _ = Insight.objects.update_or_create(
        id=iid,
        defaults=dict(
            title=title,
            summary=summary,
            is_new=is_new,
            # description은 상세 설명 필드(요약 summary와 별개)
            # 필요 시 유지하거나 비워도 됨. 여기서는 기존 로직 유지.
            description="",
        ),
    )
    # 태그
    tag_objs = []
    for text, typ in tags:
        tag, _ = InsightTag.objects.get_or_create(text=text, type=typ)
        tag_objs.append(tag)
    ins.tags.set(tag_objs)

    # 분석 아이템 리셋 후 생성
    ins.analysis_items.all().delete()
    for idx, (icon, atitle, adesc) in enumerate(analysis_items):
        InsightAnalysisItem.objects.create(
            insight=ins,
            icon=icon,
            title=atitle,
            description=adesc,
            order=idx,
        )

    # 추천(단일) upsert
    InsightRecommendation.objects.update_or_create(
        insight=ins,
        defaults=dict(
            title=rec_title,
            item_icon=rec_item_icon,
            item_title=rec_item_title,
            item_description=rec_item_desc,
        ),
    )


class Command(BaseCommand):
    help = "Seed v2 detail data for insights (10+ items)."

    @transaction.atomic
    def handle(self, *args, **options):
        dataset = [
            dict(
                iid="insight_001",
                title="주말 점심 할인 캠페인 제안",
                summary="상권 주변 기숙사생들의 주말 점심 소비 패턴을 분석하여 매출 증대를 위한 타겟팅 전략을 제안합니다.",
                tags=[("#프로모션", "growth"), ("#시간대마케팅", "retention")],
                analysis_items=[
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
                        "“기숙사”, “점심 메뉴 추천”, “혼밥 맛집” 키워드가 주말 점심에 급증했습니다.",
                    ),
                ],
                rec_title="추천 실행 계획",
                rec_item_icon="🎯",
                rec_item_title="SNS 기반 주말 점심 타겟팅 프로모션 제안",
                rec_item_desc="반경 1.5km 기숙사 타겟에게 배달앱 쿠폰+SNS 카드뉴스 조합을 오전 11시에 노출하세요.",
                is_new=True,
            ),
            dict(
                iid="insight_002",
                title="SNS 광고 예산 확대 필요",
                summary="SNS 유입의 전환 효율이 높아 예산 확대 시 매출 증대 기대.",
                tags=[("#SNS광고", "growth")],
                analysis_items=[
                    ("📊", "전환지표", "SNS 유입 전환율이 평균 대비 2배."),
                    ("🌐", "채널기여", "첫 접점 채널로 SNS 비중이 45%."),
                ],
                rec_title="집행 권장",
                rec_item_icon="🚀",
                rec_item_title="CPC 상향 및 리타겟 예산 20% 증액",
                rec_item_desc="CPC 상한 15% 상향 + 최근 7일 장바구니 이탈자 리타겟 확대.",
                is_new=True,
            ),
            dict(
                iid="insight_003",
                title="브런치 세트 프로모션 제안",
                summary="브런치 시간대의 세트 구성이 매출에 긍정적 영향을 줍니다.",
                tags=[("#세트메뉴", "growth"), ("#브런치", "retention")],
                analysis_items=[
                    ("🥐", "메뉴 선호", "빵/샐러드/음료 조합 선호 높음."),
                    ("⏰", "시간대", "10~13시 객단가가 타 시간대 대비 +12%."),
                ],
                rec_title="실행안",
                rec_item_icon="🧺",
                rec_item_title="세트 구성 고도화",
                rec_item_desc="메인+사이드+음료 세트 2종을 고정 노출하고 2주 AB 테스트.",
                is_new=True,
            ),
            dict(
                iid="insight_004",
                title="재방문 고객 혜택 필요",
                summary="재방문 고객의 이탈을 방지하기 위한 쿠폰 설계가 필요합니다.",
                tags=[("#리텐션", "retention")],
                analysis_items=[
                    ("🔁", "재방문율", "30일 내 재방문율 14%로 하락."),
                    ("💳", "혜택효과", "쿠폰 사용 시 객단가 +9%."),
                ],
                rec_title="혜택 설계",
                rec_item_icon="🎟️",
                rec_item_title="2회 방문 시 10% 할인 쿠폰",
                rec_item_desc="N+1 구조의 단계형 혜택으로 재방문 동기 강화.",
                is_new=False,
            ),
            dict(
                iid="insight_005",
                title="브랜드 인지도 강화",
                summary="자연 검색 유입이 낮아 브랜드 인지도 보완 필요.",
                tags=[("#브랜딩", "retention"), ("#경쟁대응", "expansion")],
                analysis_items=[
                    ("🔍", "검색량", "브랜드 검색량 시장 평균 대비 -30%."),
                    ("📰", "콘텐츠", "브랜드 스토리/원재료/후기형 콘텐츠 부족."),
                ],
                rec_title="브랜딩 플랜",
                rec_item_icon="📣",
                rec_item_title="브랜드 스토리 캠페인",
                rec_item_desc="제조 과정/원재료/후기형 UGC 확보 및 주 2회 발행.",
                is_new=False,
            ),
            dict(
                iid="insight_006",
                title="신규 음료 출시 기회",
                summary="여름 시즌 한정 음료 수요가 상승 중입니다.",
                tags=[("#시즌한정", "growth")],
                analysis_items=[
                    ("🍹", "검색 트렌드", "‘여름 음료’ 키워드 전주 대비 +41%.")
                ],
                rec_title="런칭 권장",
                rec_item_icon="🧊",
                rec_item_title="히비스커스/레몬 베이스 한정 음료",
                rec_item_desc="체험단 30명 모집 + 출시 첫 주 인스타 릴스 3편.",
                is_new=False,
            ),
            dict(
                iid="insight_007",
                title="주중 저녁 매출 회복",
                summary="평일 저녁 매출의 회복을 위한 타깃 세분화가 필요합니다.",
                tags=[("#오피스상권", "retention"), ("#해피아워", "growth")],
                analysis_items=[
                    ("🏙️", "시간대 변동", "18~20시 매출 -12%."),
                    ("👥", "타깃", "직장인 그룹 예약 수요 존재."),
                ],
                rec_title="해피아워",
                rec_item_icon="⏳",
                rec_item_title="주중 18~19시 한정 세트",
                rec_item_desc="직장인 대상 2인 세트 15% 할인 프로모션.",
                is_new=False,
            ),
            dict(
                iid="insight_008",
                title="경쟁사 가격 인하",
                summary="주변 경쟁사의 가격 인하로 상대적 가격 저항 발생.",
                tags=[("#경쟁분석", "expansion")],
                analysis_items=[("📉", "가격 동향", "경쟁사 평균가 -7%.")],
                rec_title="가격 대응",
                rec_item_icon="⚖️",
                rec_item_title="가격 민감 상품 한정 할인",
                rec_item_desc="주력 2품목만 ‘타임세일’로 대응, 전체 마진 유지.",
                is_new=False,
            ),
            dict(
                iid="insight_009",
                title="고객 리뷰 개선 필요",
                summary="최근 리뷰의 맛/친절 항목이 낮아졌습니다.",
                tags=[("#고객경험", "retention")],
                analysis_items=[
                    ("⭐", "평점", "최근 30일 평점 4.1 → 3.8"),
                    ("🗣️", "키워드", "‘대기’, ‘응대’ 관련 부정 키워드 증가."),
                ],
                rec_title="CX 개선",
                rec_item_icon="🤝",
                rec_item_title="리뷰 회신 + 대기 관리",
                rec_item_desc="리뷰 24시간 내 회신, 피크 아르바이트 1명 증원.",
                is_new=False,
            ),
            dict(
                iid="insight_010",
                title="테이크아웃 수요 증가",
                summary="포장 비중이 커져 대응이 필요합니다.",
                tags=[("#테이크아웃", "growth")],
                analysis_items=[("🥡", "포장율", "지난달 대비 +25%.")],
                rec_title="포장 전용 메뉴",
                rec_item_icon="🧾",
                rec_item_title="포장 최적화 패키지",
                rec_item_desc="간편 포장 가능 메뉴 카드 제작 및 진열 강화.",
                is_new=False,
            ),
        ]

        for row in dataset:
            upsert_insight_full(**row)

        self.stdout.write(
            self.style.SUCCESS(f"OK. Seeded {len(dataset)} insights (v2 detail).")
        )
