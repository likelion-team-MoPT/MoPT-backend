# ai_insights/api.py
# -----------------------------------------------------------------------------
# 목적:
# - 목록 API에서 icon/ reason_summary.icon 이 'ICON', 'ICON1' 같은 더미가 아니라
#   "내용과 관련된 진짜 이모지"가 내려가도록 응답 단계에서 계산해서 채웁니다.
#
# 방법:
# - DB 값은 그대로 두되, 응답 직전에 title/태그 등으로 아이콘을 추론하여 주입
# - 우선순위: "제목 키워드 매핑" > "태그 타입 매핑(growth/retention/expansion)"
# - 신규(is_new=True): reason_summary.icon 을 계산해 교체
# - 기존(is_new=False): item.icon 필드를 계산해 교체
#
# 장점:
# - 마이그레이션/시드 수정 없이 즉시 반영
# - 팀원 코드와 충돌 적음(뷰/스키마 변경 없음)
# -----------------------------------------------------------------------------

from typing import List, Optional

from django.shortcuts import get_object_or_404
from ninja import Router, Schema

from .models import (
    Insight,
    InsightAnalysisItem,
    InsightRecommendation,
    InsightTag,
)

router = Router()

# ======= Schemas (OpenAPI 스키마) =======


class TagSchema(Schema):
    text: str
    type: str  # 'growth' | 'retention' | 'expansion'


class ReasonSummarySchema(Schema):
    icon: str
    text: str


class NewStrategySchema(Schema):
    id: str
    title: str
    reason_summary: ReasonSummarySchema
    created_at: str
    isNew: bool


class RecommendedStrategySchema(Schema):
    id: str
    icon: str
    title: str
    tags: List[TagSchema]


# 상세 V2 포맷
class AnalysisItemSchema(Schema):
    icon: str
    title: str
    description: str


class AnalysisSchema(Schema):
    title: str
    items: List[AnalysisItemSchema]


class RecommendationItemSchema(Schema):
    icon: str
    title: str
    description: str


class RecommendationSchema(Schema):
    title: str
    item: RecommendationItemSchema


class InsightDetailV2Schema(Schema):
    id: str
    tags: List[TagSchema]
    title: str
    summary: Optional[str]
    analysis: AnalysisSchema
    recommendation: Optional[RecommendationSchema]


# ======= 이모지 매핑 규칙 =======
# 1) 제목 키워드 → 이모지 (가장 높은 우선순위)
TITLE_KEYWORD_EMOJI = [
    # (키워드, 이모지)
    ("브런치", "🥐"),
    ("세트", "🧺"),
    ("주말", "🗓️"),
    ("점심", "🍱"),
    ("할인", "🏷️"),
    ("SNS", "📣"),
    ("광고", "🚀"),
    ("예산", "💰"),
    ("리텐션", "🔁"),
    ("재방문", "🔁"),
    ("리뷰", "⭐"),
    ("고객", "🧑‍🤝‍🧑"),
    ("브랜드", "🏷️"),
    ("인지도", "📈"),
    ("가격", "⚖️"),
    ("경쟁", "🥊"),
    ("신규", "✨"),
    ("음료", "🥤"),
    ("여름", "🌞"),
    ("테이크아웃", "🥡"),
    ("런치", "🍱"),
    ("해피아워", "⏳"),
    ("오피스", "🏙️"),
]

# 2) 태그 타입 → 이모지 (제목과 매칭 안 되면 사용)
TAG_TYPE_EMOJI = {
    "growth": "📈",
    "retention": "🔁",
    "expansion": "🧭",
}

# 3) 세부 태그 텍스트 힌트(선택): 태그에 해시가 포함된 경우도 고려
TAG_TEXT_HINTS = [
    ("#브런치", "🥐"),
    ("#테이크아웃", "🥡"),
    ("#해피아워", "⏳"),
    ("#고객경험", "🤝"),
    ("#경쟁분석", "⚖️"),
    ("#SNS", "📣"),
    ("#프로모션", "🎯"),
]

# ======= 헬퍼 =======


def _tags_for(insight: Insight) -> List[TagSchema]:
    return [
        TagSchema(text=t.text, type=t.type) for t in insight.tags.all().order_by("id")
    ]


def _pick_emoji_from_title(title: str) -> Optional[str]:
    """제목의 키워드를 보고 가장 먼저 일치하는 이모지를 반환"""
    if not title:
        return None
    t = title.upper()
    for kw, emo in TITLE_KEYWORD_EMOJI:
        if kw.upper() in t:
            return emo
    return None


def _pick_emoji_from_tags(insight: Insight) -> Optional[str]:
    """
    태그로 이모지 추론:
    - 먼저 텍스트 힌트(#브런치 등)가 있으면 그걸 사용
    - 없으면 type(growth/retention/expansion)으로 매핑
    """
    tags = list(insight.tags.all())
    # 텍스트 힌트 우선
    for hint, emo in TAG_TEXT_HINTS:
        for t in tags:
            if hint in (t.text or ""):
                return emo
    # type 기반(첫 번째 태그 우선)
    for t in tags:
        emo = TAG_TYPE_EMOJI.get(t.type or "")
        if emo:
            return emo
    return None


def _pick_icon_for_new(insight: Insight) -> str:
    """
    신규 카드(is_new=True)의 reason_summary.icon 을 채울 때 사용.
    규칙: 제목 키워드 → 태그 → 기본값
    """
    # 1) 제목 기반
    emo = _pick_emoji_from_title(insight.title)
    if emo:
        return emo
    # 2) 태그 기반
    emo = _pick_emoji_from_tags(insight)
    if emo:
        return emo
    # 3) 기본값
    return "✨"


def _pick_icon_for_recommended(insight: Insight) -> str:
    """
    기존 카드(is_new=False)의 목록 아이콘을 채울 때 사용.
    규칙: 제목 키워드 → 태그 → 기본값
    """
    emo = _pick_emoji_from_title(insight.title)
    if emo:
        return emo
    emo = _pick_emoji_from_tags(insight)
    if emo:
        return emo
    return "📌"


def _new_strategy_payload(qs):
    """
    기존 reason_summary.icon 값(ICON1/2/3 등)을 무시하고
    내용 기반 이모지로 대체해 내려줍니다.
    """
    out = []
    for i in qs:
        computed_icon = _pick_icon_for_new(i)
        out.append(
            NewStrategySchema(
                id=i.id,
                title=i.title,
                reason_summary=ReasonSummarySchema(
                    icon=computed_icon,  # ✅ 여기서 치환!
                    text=i.reason_text or "",
                ),
                created_at=i.created_at.isoformat(),
                isNew=bool(i.is_new),
            )
        )
    return out


def _recommended_payload(qs):
    """
    기존 icon 필드가 'ICON' 등 더미여도,
    계산된 이모지로 대체해서 내려줍니다.
    """
    out = []
    for i in qs:
        computed_icon = _pick_icon_for_recommended(i)
        out.append(
            RecommendedStrategySchema(
                id=i.id,
                icon=computed_icon,  # ✅ 여기서 치환!
                title=i.title,
                tags=_tags_for(i),
            )
        )
    return out


def _detail_v2_payload(insight: Insight) -> InsightDetailV2Schema:
    # analysis
    items_qs = InsightAnalysisItem.objects.filter(insight=insight).order_by(
        "order", "id"
    )
    items = [
        AnalysisItemSchema(
            icon=x.icon or "", title=x.title or "", description=x.description or ""
        )
        for x in items_qs
    ]
    analysis = AnalysisSchema(title="AI 분석 근거", items=items)

    # recommendation (없을 수도 있음)
    rec = InsightRecommendation.objects.filter(insight=insight).first()
    recommendation = None
    if rec:
        recommendation = RecommendationSchema(
            title=rec.title or "추천 실행 계획",
            item=RecommendationItemSchema(
                icon=rec.item_icon or "",
                title=rec.item_title or "",
                description=rec.item_description or "",
            ),
        )

    return InsightDetailV2Schema(
        id=insight.id,
        tags=_tags_for(insight),
        title=insight.title,
        summary=insight.summary,
        analysis=analysis,
        recommendation=recommendation,
    )


# ======= Endpoints =======


@router.get(
    "",
    tags=["AI 인사이트"],
    summary="AI 인사이트(신규/기존) 목록",
)
def list_insights(request, kind: Optional[str] = None):
    """
    - GET /api/v1/insights
    - GET /api/v1/insights?kind=new
    - GET /api/v1/insights?kind=recommended

    변경점:
    - 응답 생성 시 내용 기반 이모지로 icon 을 계산해 내려줍니다.
    """
    kind = (kind or "").lower()

    if kind == "new":
        qs_new = Insight.objects.filter(is_new=True).order_by("-created_at")
        return {"new_strategies": _new_strategy_payload(qs_new)}

    if kind == "recommended":
        qs_rec = Insight.objects.filter(is_new=False).order_by("-created_at")
        return {"recommended_strategies": _recommended_payload(qs_rec)}

    qs_new = Insight.objects.filter(is_new=True).order_by("-created_at")
    qs_rec = Insight.objects.filter(is_new=False).order_by("-created_at")
    return {
        "new_strategies": _new_strategy_payload(qs_new),
        "recommended_strategies": _recommended_payload(qs_rec),
    }


@router.get(
    "/{insight_id}",
    response=InsightDetailV2Schema,
    tags=["AI 인사이트"],
    summary="AI 인사이트 상세 (V2 포맷)",
)
def retrieve_insight_v2(request, insight_id: str):
    """
    GET /api/v1/insights/{insight_id}
    (상세는 기존 로직 유지: analysis/recommendation의 아이콘은 DB 값 사용)
    """
    insight = get_object_or_404(Insight, id=insight_id)
    return _detail_v2_payload(insight)
