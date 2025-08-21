# ai_insights/management/commands/seed_insight_details.py
# 전체 교체본 (주석 자세히)
from django.core.management.base import BaseCommand

from ai_insights.models import (
    Insight,
    InsightAnalysisItem,
    InsightRecommendation,
    InsightTag,
)

DATA = {
    # ... (네가 준 DATA 그대로 유지) ...
}


def _get_or_create_tags(tag_pairs):
    """[('#프로모션','growth'), ...] -> [InsightTag, ...]"""
    result = []
    for text, typ in tag_pairs:
        tag, _ = InsightTag.objects.get_or_create(text=text, type=typ)
        result.append(tag)
    return result


def upsert_detail(ins: Insight, payload: dict):
    # ✅ 요약(summary) 필드에 저장해야 V2 응답에 뜬다
    new_summary = payload.get("summary")
    if new_summary:
        ins.summary = new_summary

    # 태그
    tags = _get_or_create_tags(payload.get("tags", []))
    if tags:
        ins.tags.set(tags)

    # 분석 아이템(리셋 후 생성)
    ins.analysis_items.all().delete()
    for idx, item in enumerate(payload.get("analysis", [])):
        InsightAnalysisItem.objects.create(
            insight=ins,
            icon=item.get("icon", "") or "",
            title=item.get("title", "") or "",
            description=item.get("description", "") or "",
            order=idx,
        )

    # 추천(단일) upsert
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

    # ✅ 요약 수정분 반영
    ins.save(update_fields=["summary"])  # summary만 바뀐 경우 빠르게 저장


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
