# ai_insights/management/commands/patch_insight_reason_and_icons.py
# -------------------------------------------------------------------
# 목적:
#  - is_new=True 인 Insight의 reason_summary(icon/text)가 비어 있으면 채워줍니다.
#  - is_new=False 인 Insight의 icon 값을 ""(빈값)으로 통일합니다.
#
# 특징:
#  - 여러 번 실행해도 안전(idempotent)
#  - 기존 값이 이미 있으면 건드리지 않음
#  - 매핑에 없는 신규 카드가 있어도 "기본 문구"로 채워줌
#
# 사용:
#   poetry run python manage.py patch_insight_reason_and_icons
# -------------------------------------------------------------------
from django.core.management.base import BaseCommand

from ai_insights.models import Insight

# is_new=True 카드 기본 매핑 (seed_insights.py의 reason_text와 일치시킴)
DEFAULT_REASON_BY_ID = {
    "insight_001": ("ICON1", "최근 3주간 점심 시간대 매출 상승"),
    "insight_002": ("ICON2", "SNS 유입 전환율이 평균보다 2배 높음"),
    "insight_003": ("ICON3", "브런치 키워드 검색량 40% 증가"),
}

# 매핑에 없는 신규 카드가 있을 때 사용할 기본값
FALLBACK_REASON = ("", "데이터 기반 신규 전략 제안")


class Command(BaseCommand):
    help = "Patch is_new reason_summary (if empty) and unify icon for non-new insights."

    def handle(self, *args, **options):
        filled_new = 0
        kept_new = 0
        updated_old = 0

        # 1) is_new=True: reason_icon/reason_text 비어 있으면 채우기
        for ins in Insight.objects.filter(is_new=True):
            icon = (ins.reason_icon or "").strip()
            text = (ins.reason_text or "").strip()

            if icon and text:
                kept_new += 1
                continue

            # 매핑 우선, 없으면 fallback
            icon_new, text_new = DEFAULT_REASON_BY_ID.get(ins.id, FALLBACK_REASON)

            # 기존 값이 일부만 비어 있으면 비어있는 것만 채움
            if not icon:
                ins.reason_icon = icon_new
            if not text:
                ins.reason_text = text_new

            ins.save(update_fields=["reason_icon", "reason_text"])
            filled_new += 1
            self.stdout.write(self.style.SUCCESS(f"filled reason_summary: {ins.id}"))

        # 2) is_new=False: icon을 ""(빈값)으로 통일
        #    (신규 카드와 같은 규칙으로 맞추고 싶다는 요구사항 반영)
        qs_old = Insight.objects.filter(is_new=False).exclude(icon="")
        updated_old = qs_old.update(icon="")

        # 결과 요약
        self.stdout.write(
            self.style.SUCCESS("=== patch_insight_reason_and_icons 결과 ===")
        )
        self.stdout.write(f"is_new=True  : 채움 {filled_new}건 / 유지 {kept_new}건")
        self.stdout.write(f"is_new=False : icon 빈값으로 통일 {updated_old}건")
        self.stdout.write(self.style.SUCCESS("완료."))
