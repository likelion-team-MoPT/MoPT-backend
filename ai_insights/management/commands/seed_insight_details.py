# ai_insights/management/commands/seed_insight_details.py
from django.core.management.base import BaseCommand
from django.utils import timezone

from ai_insights.models import (
    Insight,
    InsightAnalysisItem,
    InsightRecommendation,
    InsightTag,
)

# ⚠️ 콘솔 인코딩 문제(윈도우) 피하려고 print 내용은 ASCII만 사용합니다.
#    데이터에는 이모지 포함되어도 DB 저장은 문제 없습니다(콘솔에 그대로 출력만 피함).

DATA = {
    "insight_001": {
        "tags": [("#프로모션", "growth"), ("#시간대마케팅", "retention")],
        "summary": "상권 주변 기숙사생들의 주말 점심 소비 패턴을 분석하여 매출 증대를 위한 타겟팅 전략을 제안합니다.",
        "analysis": [
            {
                "icon": "🧾",
                "title": "매출 데이터",
                "description": "최근 3주간 주말 점심 매출이 평균 대비 18% 상승하였습니다.",
            },
            {
                "icon": "📍",
                "title": "시장 데이터",
                "description": "상권 내 기숙사생들의 주말 외식 빈도가 다른 요일 대비 높게 나타났습니다.",
            },
            {
                "icon": "💬",
                "title": "SNS 트렌드",
                "description": "“기숙사”, “점심 메뉴 추천”, “혼밥 맛집” 관련 키워드가 주말 점심 시간대에 SNS에서 급증하였습니다.",
            },
        ],
        "recommendation": {
            "title": "추천 실행 계획",
            "item_icon": "🎯",
            "item_title": "SNS 기반 주말 점심 타겟팅 프로모션 제안",
            "item_description": "주변 기숙사 반경 1.5km 내 타겟 유저에게 배달앱 쿠폰 + SNS 홍보용 메뉴 카드 콘텐츠 조합을 추천합니다.\n점심 전 타이밍(오전 11시)에 메시지를 발송하여 “혼밥 할인 세트”를 노출하세요!",
        },
    },
    "insight_002": {
        "tags": [("#광고", "growth"), ("#SNS전환", "retention")],
        "summary": "SNS 유입 대비 전환 효율이 높아 광고 예산 증액 시 성과 개선 여지가 큽니다.",
        "analysis": [
            {
                "icon": "📈",
                "title": "전환 데이터",
                "description": "최근 2주간 SNS 전환율이 평균 대비 2배 높게 유지되고 있습니다.",
            },
            {
                "icon": "💵",
                "title": "CAC 비교",
                "description": "동일 예산 대비 SNS 채널 CAC가 다른 채널보다 23% 낮게 나타납니다.",
            },
            {
                "icon": "🧭",
                "title": "고객 경로",
                "description": "SNS → 랜딩 → 배달앱로 이어지는 경로에서 이탈률이 낮습니다.",
            },
        ],
        "recommendation": {
            "title": "추천 실행 계획",
            "item_icon": "🚀",
            "item_title": "SNS 예산 20~30% 증액 및 성과형 캠페인 확대",
            "item_description": "클릭-전환 최적화 캠페인 비중을 늘리고, 상위 3개 크리에이티브에 예산을 집중하세요.",
        },
    },
    "insight_003": {
        "tags": [("#브런치", "growth"), ("#메뉴기획", "expansion")],
        "summary": "브런치 키워드 수요가 증가하는 시점에 세트 구성 최적화를 통해 매출 확대를 노립니다.",
        "analysis": [
            {
                "icon": "🔍",
                "title": "검색 트렌드",
                "description": "브런치 키워드 검색량이 전월 대비 40% 증가했습니다.",
            },
            {
                "icon": "🍽️",
                "title": "메뉴 선호",
                "description": "샌드/커피 조합의 주문 빈도가 동시간대 타 메뉴보다 28% 높습니다.",
            },
            {
                "icon": "🕒",
                "title": "시간대 특성",
                "description": "토·일 10~13시 주문 집중도가 평일 대비 1.7배 높습니다.",
            },
        ],
        "recommendation": {
            "title": "추천 실행 계획",
            "item_icon": "🧺",
            "item_title": "브런치 세트(메인+음료) 번들 출시",
            "item_description": "세트 구매 시 10% 할인과 포토카드 증정 이벤트를 함께 운영하세요.",
        },
    },
    "insight_004": {
        "tags": [("#리텐션", "retention"), ("#혜택설계", "retention")],
        "summary": "재방문 고객 비중이 늘어나는 구간에서 충성도 프로그램을 정교화합니다.",
        "analysis": [
            {
                "icon": "🔁",
                "title": "재구매율",
                "description": "최근 30일 재구매율이 14%p 상승했습니다.",
            },
            {
                "icon": "🎁",
                "title": "혜택 반응",
                "description": "도장/포인트 적립 참여율이 1개월 전 대비 31% 늘었습니다.",
            },
            {
                "icon": "📊",
                "title": "세그먼트",
                "description": "평균 구매주기 9~12일 세그먼트가 전체의 26%를 차지합니다.",
            },
        ],
        "recommendation": {
            "title": "추천 실행 계획",
            "item_icon": "🏷️",
            "item_title": "N+1 쿠폰/등급별 혜택 리뉴얼",
            "item_description": "3회 방문 시 무료 사이드 제공, VIP 5% 상시 할인으로 LTV를 증대하세요.",
        },
    },
    "insight_005": {
        "tags": [("#브랜딩", "retention"), ("#경쟁분석", "expansion")],
        "summary": "브랜드 검색량이 낮아 상위 퍼널 인지도 제고가 필요합니다.",
        "analysis": [
            {
                "icon": "🔎",
                "title": "브랜드 검색",
                "description": "브랜드 키워드 검색량이 지역 평균 대비 30% 낮습니다.",
            },
            {
                "icon": "🏁",
                "title": "경쟁사 비교",
                "description": "경쟁 A, B 대비 SNS 언급량도 열세입니다.",
            },
            {
                "icon": "🖼️",
                "title": "자산 활용",
                "description": "시그니처 메뉴 비주얼 자산의 재활용도가 낮습니다.",
            },
        ],
        "recommendation": {
            "title": "추천 실행 계획",
            "item_icon": "📣",
            "item_title": "시그니처 캠페인 및 지역 해시태그 확산",
            "item_description": "시즌 해시태그 + 사용자 참여형 UGC 이벤트로 상위 퍼널 인지도를 끌어올리세요.",
        },
    },
    "insight_006": {
        "tags": [("#신메뉴", "growth"), ("#여름음료", "growth")],
        "summary": "기온 상승과 함께 청량 음료 수요가 커지고 있어 신제품 출시 적기입니다.",
        "analysis": [
            {
                "icon": "🌡️",
                "title": "기상 영향",
                "description": "평균 기온 2℃ 상승 구간에서 냉음료 매출이 19% 증가했습니다.",
            },
            {
                "icon": "🥤",
                "title": "메뉴 트렌드",
                "description": "상권 내 과일·에이드 계열의 검색량이 뚜렷이 증가합니다.",
            },
            {
                "icon": "🧪",
                "title": "테스트 반응",
                "description": "시음 이벤트에서 재구매 의향 72%가 확인되었습니다.",
            },
        ],
        "recommendation": {
            "title": "추천 실행 계획",
            "item_icon": "🧊",
            "item_title": "여름 한정 신메뉴 론칭 + 세트 번들",
            "item_description": "런칭 첫 주 인스타 릴스/스토리 집중 송출과 번들(음료+디저트) 운영을 권장합니다.",
        },
    },
    "insight_007": {
        "tags": [("#비수기해소", "growth"), ("#저녁타임", "retention")],
        "summary": "주중 저녁 매출 저하 구간에 시간대 특화 프로모션을 적용해 회복을 돕습니다.",
        "analysis": [
            {
                "icon": "⏰",
                "title": "시간대 매출",
                "description": "18~20시 매출이 전체 평균 대비 22% 낮습니다.",
            },
            {
                "icon": "👥",
                "title": "방문 패턴",
                "description": "2인 방문 비중이 높아 공유형 메뉴 선호가 나타납니다.",
            },
            {
                "icon": "💳",
                "title": "결제 단가",
                "description": "저녁 시간대 객단가가 점심 대비 15% 낮습니다.",
            },
        ],
        "recommendation": {
            "title": "추천 실행 계획",
            "item_icon": "🎫",
            "item_title": "주중 저녁 전용 세트/타임세일",
            "item_description": "18~20시 한정 콤보 세트 10% 할인 + 스탬프 2배 적립을 병행하세요.",
        },
    },
    "insight_008": {
        "tags": [("#가격정책", "expansion"), ("#경쟁모니터링", "expansion")],
        "summary": "경쟁사 가격 인하 이슈에 대응해 민감 메뉴를 중심으로 전략을 재정렬합니다.",
        "analysis": [
            {
                "icon": "🏷️",
                "title": "가격 민감도",
                "description": "핵심 메뉴 3종의 탄력성이 높은 편입니다.",
            },
            {
                "icon": "🧮",
                "title": "마진 분석",
                "description": "동일 메뉴의 재료비 상승으로 마진율 3%p 하락 추세입니다.",
            },
            {
                "icon": "📈",
                "title": "수요 대체",
                "description": "경쟁사 할인 기간에 주문 이탈이 관측됩니다.",
            },
        ],
        "recommendation": {
            "title": "추천 실행 계획",
            "item_icon": "⚖️",
            "item_title": "가격 방어 + 가치 강조",
            "item_description": "세트 업셀/가치 메시지 강화로 가격 민감도를 완화하고 민감 메뉴는 한시 번들로 대응하세요.",
        },
    },
    "insight_009": {
        "tags": [("#리뷰개선", "retention"), ("#고객경험", "retention")],
        "summary": "리뷰 평점/응답속도 개선을 통해 전환·재방문을 함께 끌어올립니다.",
        "analysis": [
            {
                "icon": "⭐",
                "title": "평점 분포",
                "description": "최근 14일 3★ 이하 리뷰 비중이 높아졌습니다.",
            },
            {
                "icon": "💬",
                "title": "응답 속도",
                "description": "리뷰 응답 평균 19시간으로 상권 평균을 상회합니다.",
            },
            {
                "icon": "🧩",
                "title": "원인 분석",
                "description": "포장 온도/포장재 관련 피드백이 반복됩니다.",
            },
        ],
        "recommendation": {
            "title": "추천 실행 계획",
            "item_icon": "🛠️",
            "item_title": "리뷰 SLA·템플릿 도입",
            "item_description": "응답 SLA 6시간, 개선 약속 템플릿을 도입하고 포장재 옵션을 개선하세요.",
        },
    },
    "insight_010": {
        "tags": [("#테이크아웃", "growth"), ("#동선최적화", "retention")],
        "summary": "테이크아웃 수요가 늘며 회전율 개선과 대기 체감 감소가 중요해졌습니다.",
        "analysis": [
            {
                "icon": "🚶",
                "title": "주문 채널",
                "description": "포장 주문 비중이 25%로 상승했습니다.",
            },
            {
                "icon": "📦",
                "title": "포장 효율",
                "description": "피크타임 포장 대기 시간이 6분을 초과합니다.",
            },
            {
                "icon": "🧭",
                "title": "매장 동선",
                "description": "픽업 스테이션 분리가 미흡하여 체감 대기가 커집니다.",
            },
        ],
        "recommendation": {
            "title": "추천 실행 계획",
            "item_icon": "📍",
            "item_title": "픽업 스테이션/사전주문 개선",
            "item_description": "픽업 존 분리와 사전주문 안내를 강화해 체감 대기를 줄이고 회전율을 높이세요.",
        },
    },
}


def _get_or_create_tags(tag_pairs):
    """
    tag_pairs: [("#프로모션","growth"), ...]
    returns: [InsightTag, ...]
    """
    result = []
    for text, typ in tag_pairs:
        tag, _ = InsightTag.objects.get_or_create(text=text, type=typ)
        result.append(tag)
    return result


def upsert_detail(ins: Insight, payload: dict):
    # summary
    ins.description = payload.get("summary") or ins.description
    # 태그
    tags = _get_or_create_tags(payload.get("tags", []))
    if tags:
        ins.tags.set(tags)

    # 분석 아이템
    ins.analysis_items.all().delete()
    items = payload.get("analysis", [])
    for idx, item in enumerate(items):
        InsightAnalysisItem.objects.create(
            insight=ins,
            icon=item.get("icon", "") or "",
            title=item.get("title", "") or "",
            description=item.get("description", "") or "",
            order=idx,
        )

    # 추천(상세 1개)
    rec = payload.get("recommendation")
    if rec:
        InsightRecommendation.objects.update_or_create(
            insight=ins,
            defaults=dict(
                title=rec.get("title", "") or "",
                item_icon=rec.get("item_icon", "") or "",
                item_title=rec.get("item_title", "") or "",
                item_description=rec.get("item_description", "") or "",
            ),
        )


class Command(BaseCommand):
    help = "Seed/Update insight details (summary/analysis/recommendation) for insights 001~010"

    def handle(self, *args, **options):
        updated = 0
        for ins in Insight.objects.filter(id__in=list(DATA.keys())):
            payload = DATA.get(ins.id)
            if not payload:
                continue
            upsert_detail(ins, payload)
            updated += 1
        self.stdout.write(self.style.SUCCESS(f"done. updated: {updated} insights"))
