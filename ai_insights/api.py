# ai_insights/api.py
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


# 상세 V2 포맷 (네가 원하는 2번 형식)
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


# ======= 헬퍼 =======


def _tags_for(insight: Insight) -> List[TagSchema]:
    return [
        TagSchema(text=t.text, type=t.type) for t in insight.tags.all().order_by("id")
    ]


def _new_strategy_payload(qs):
    out = []
    for i in qs:
        out.append(
            NewStrategySchema(
                id=i.id,
                title=i.title,
                reason_summary=ReasonSummarySchema(
                    icon=i.reason_icon or "",
                    text=i.reason_text or "",
                ),
                created_at=i.created_at.isoformat(),
                isNew=bool(i.is_new),
            )
        )
    return out


def _recommended_payload(qs):
    out = []
    for i in qs:
        out.append(
            RecommendedStrategySchema(
                id=i.id,
                icon=i.icon or "ICON",
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
        summary=insight.summary,  # models에 summary 필드 추가해뒀다면 사용, 없으면 None
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
    -> 2번 형식(요청한 상세 포맷)으로 반환
    """
    insight = get_object_or_404(Insight, id=insight_id)
    return _detail_v2_payload(insight)
