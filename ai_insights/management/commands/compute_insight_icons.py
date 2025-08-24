# ai_insights/management/commands/compute_insight_icons.py
# ------------------------------------------------------------
# 목적:
#  - Insight 레코드의 아이콘 필드를 "내용 기반 이모지"로 채웁니다.
#  - is_new=True  → reason_icon (reason_summary.icon)
#  - is_new=False → icon (목록용 아이콘)
#
# 특징:
#  - 제목 키워드 매핑 > 태그 텍스트 힌트 > 태그 타입 매핑 > 기본값
#  - 여러 번 실행해도 안전(idempotent)
#  - --dry-run 으로 변경 내역만 미리 보기
# ------------------------------------------------------------
from django.core.management.base import BaseCommand

from ai_insights.models import Insight

# 1) 제목 키워드 → 이모지 (우선순위 1)
TITLE_KEYWORD_EMOJI = [
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

# 2) 태그 텍스트 힌트 (우선순위 2)
TAG_TEXT_HINTS = [
    ("#브런치", "🥐"),
    ("#테이크아웃", "🥡"),
    ("#해피아워", "⏳"),
    ("#고객경험", "🤝"),
    ("#경쟁분석", "⚖️"),
    ("#SNS", "📣"),
    ("#프로모션", "🎯"),
]

# 3) 태그 타입 매핑 (우선순위 3)
TAG_TYPE_EMOJI = {
    "growth": "📈",
    "retention": "🔁",
    "expansion": "🧭",
}


def pick_emoji_from_title(title: str) -> str | None:
    if not title:
        return None
    t = title.upper()
    for kw, emo in TITLE_KEYWORD_EMOJI:
        if kw.upper() in t:
            return emo
    return None


def pick_emoji_from_tags(insight: Insight) -> str | None:
    tags = list(insight.tags.all())
    # 텍스트 힌트 우선
    for hint, emo in TAG_TEXT_HINTS:
        for t in tags:
            if hint in (t.text or ""):
                return emo
    # 타입 기반
    for t in tags:
        emo = TAG_TYPE_EMOJI.get(t.type or "")
        if emo:
            return emo
    return None


def compute_for_new(insight: Insight) -> str:
    # 신규(is_new=True): reason_icon 채움
    emo = pick_emoji_from_title(insight.title)
    if emo:
        return emo
    emo = pick_emoji_from_tags(insight)
    if emo:
        return emo
    return "✨"  # 기본


def compute_for_recommended(insight: Insight) -> str:
    # 기존(is_new=False): icon 채움
    emo = pick_emoji_from_title(insight.title)
    if emo:
        return emo
    emo = pick_emoji_from_tags(insight)
    if emo:
        return emo
    return "📌"  # 기본


class Command(BaseCommand):
    help = "Compute and persist emoji icons for insights (reason_icon/icon)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="DB에 저장하지 않고 변경 예정만 출력합니다.",
        )

    def handle(self, *args, **opts):
        dry = opts["dry_run"]
        patched_new = 0
        patched_old = 0

        # 신규 카드 → reason_icon 채우기
        for ins in Insight.objects.filter(is_new=True):
            new_icon = compute_for_new(ins)
            old_icon = ins.reason_icon or ""
            if old_icon != new_icon:
                self.stdout.write(
                    f"[NEW ] {ins.id} '{ins.title}': {old_icon} -> {new_icon}"
                )
                if not dry:
                    ins.reason_icon = new_icon
                    ins.save(update_fields=["reason_icon"])
                patched_new += 1

        # 기존 카드 → icon 채우기
        for ins in Insight.objects.filter(is_new=False):
            new_icon = compute_for_recommended(ins)
            old_icon = ins.icon or ""
            if old_icon != new_icon:
                self.stdout.write(
                    f"[RECO] {ins.id} '{ins.title}': {old_icon} -> {new_icon}"
                )
                if not dry:
                    ins.icon = new_icon
                    ins.save(update_fields=["icon"])
                patched_old += 1

        self.stdout.write(self.style.SUCCESS("=== compute_insight_icons 결과 ==="))
        self.stdout.write(f"is_new=True  patched: {patched_new}")
        self.stdout.write(f"is_new=False patched: {patched_old}")
        self.stdout.write(self.style.SUCCESS("완료."))
