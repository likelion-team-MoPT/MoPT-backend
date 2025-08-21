# ai_insights/management/commands/seed_insight_patch_011_012.py
# ------------------------------------------------------------
# 목적: insight_011 / insight_012 의 summary 누락을 채우기 위한
#       "작은 패치" 커맨드. 기존 시더 파일을 수정하지 않아
#       팀 머지 충돌 위험이 낮습니다.
# 사용:
#   poetry run python manage.py seed_insight_patch_011_012
#   (여러 번 실행해도 안전)
# ------------------------------------------------------------
from django.core.management.base import BaseCommand

from ai_insights.models import Insight

PATCH_DATA = {
    # 기존 제목: "직장인 런치 세트 최적화"
    "insight_011": (
        "오피스 상권의 평일 11:30~13:30 주문 집중도와 객단가 변화를 분석해 "
        "런치 세트 구성/가격대를 최적화합니다. 주력 메뉴+사이드 조합과 대기시간을 고려한 "
        "간편 메뉴 구성을 통해 회전율과 체감 대기를 함께 개선합니다."
    ),
    # 기존 제목: "로열티 프로그램 도입"
    "insight_012": (
        "최근 재방문 주기와 적립/쿠폰 사용 데이터를 기반으로 등급제·스탬프형 로열티 프로그램을 도입합니다. "
        "방문 2·4·6회 구간에서 차등 혜택을 제공해 재방문 빈도와 LTV 상승을 목표로 합니다."
    ),
}


class Command(BaseCommand):
    help = "Fill missing summary for insights 011 and 012 (safe to re-run)."

    def handle(self, *args, **options):
        updated = 0
        for iid, summary in PATCH_DATA.items():
            try:
                ins = Insight.objects.get(id=iid)
            except Insight.DoesNotExist:
                # 목록 시더가 아직 안 돌았다면 스킵
                self.stdout.write(self.style.WARNING(f"skip: {iid} not found"))
                continue

            # 비어 있거나 다르면 업데이트 (여러 번 실행해도 안전)
            if (ins.summary or "").strip() != summary.strip():
                ins.summary = summary
                ins.save(update_fields=["summary"])
                updated += 1
                self.stdout.write(self.style.SUCCESS(f"updated: {iid}"))

        self.stdout.write(self.style.SUCCESS(f"done. updated={updated}"))
