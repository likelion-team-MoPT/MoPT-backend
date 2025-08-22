# home/management/commands/normalize_trend_keywords.py
# ------------------------------------------------------------
# 목적:
# - TrendKeyword.region 값을 정규화(별칭→정식명)하고
# - (region, keyword) 중복을 자동으로 정리합니다.
#
# 특징:
# - REGION_MAP 에 정의된 alias -> canonical 로 통일
# - 이미 동일 (canonical, keyword) 가 있으면 중복 레코드 삭제
# - --dry-run 옵션으로 변경/삭제 내역을 미리 확인 가능
# - --casefold 옵션으로 대소문자/공백 차이를 관용 처리
# - 여러 번 실행해도 안전(idempotent)
#
# 사용 예:
#   poetry run python manage.py normalize_trend_keywords
#   poetry run python manage.py normalize_trend_keywords --dry-run
#   poetry run python manage.py normalize_trend_keywords --casefold
#   poetry run python manage.py normalize_trend_keywords --dry-run --casefold
# ------------------------------------------------------------
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.utils import IntegrityError

from home.models import TrendKeyword

# ✅ 지역명 매핑 테이블(필요 시 자유롭게 확장)
#  - "alias": "canonical"
REGION_MAP: dict[str, str] = {
    # 서울 주요 구 (예: 축약을 정식 행정구로)
    "강남": "강남구",
    "강북": "강북구",
    "마포": "마포구",
    "서초": "서초구",
    "송파": "송파구",
    "강동": "강동구",
    "동대문": "동대문구",
    "종로": "종로구",
    "중": "중구",
    "광진": "광진구",
    "성동": "성동구",
    "은평": "은평구",
    "노원": "노원구",
    "구로": "구로구",
    "금천": "금천구",
    "양천": "양천구",
    "영등포": "영등포구",
    "서대문": "서대문구",
    # 요청 지역
    "모현": "모현읍",
    # 필요 시 계속 추가...
}


def _norm(s: str, casefold: bool) -> str:
    """
    문자열 전처리: 앞뒤 공백 제거 (+ 선택적으로 casefold)
    """
    if s is None:
        return s
    s2 = s.strip()
    return s2.casefold() if casefold else s2


class Command(BaseCommand):
    help = (
        "Normalize TrendKeyword.region by alias map and deduplicate (region, keyword)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="실제로 저장/삭제하지 않고 변경 예정 내역만 출력합니다.",
        )
        parser.add_argument(
            "--casefold",
            action="store_true",
            help="지역명 비교 시 대소문자/공백 차이를 관용 처리합니다.",
        )
        parser.add_argument(
            "--verbose-rows",
            action="store_true",
            help="개별 레코드 변경/삭제 로그를 자세히 출력합니다.",
        )

    def handle(self, *args, **options):
        dry_run: bool = options["dry_run"]
        casefold: bool = options["casefold"]
        verbose_rows: bool = options["verbose_rows"]

        # 통계 카운터
        scanned = 0
        to_update = 0
        actually_updated = 0
        merged_deleted = 0
        skipped = 0

        # 빠른 조회용 전체 레코드
        qs = TrendKeyword.objects.all().only("id", "region", "keyword")
        scanned = qs.count()

        # alias/canonical 비교를 빠르게 하기 위한 보조 맵
        #   key = (norm(region), norm(keyword))  → id set
        #   canonical 존재 여부 확인에 사용
        def key(region: str, kw: str) -> tuple[str, str]:
            return _norm(region, casefold), _norm(kw, casefold)

        # 현재 DB 스냅샷 (canonical 존재 확인/중복 체크에 사용)
        existing = {}
        for tk in qs:
            existing.setdefault(key(tk.region, tk.keyword), set()).add(tk.id)

        # 메인 루프
        # - REGION_MAP 의 alias 를 모두 돌며 해당 region 레코드를 canonical 로 이동
        # - 이동하려는 (canonical, keyword) 가 이미 있으면 현재 레코드를 삭제(merge)
        # - dry-run 이면 DB 반영 없이 로그/카운트만
        if dry_run:
            self.stdout.write(self.style.WARNING("** DRY-RUN 모드로 실행합니다 **"))

        # 트랜잭션(실행 시에만). dry-run 은 읽기만 하므로 트랜잭션 불필요
        ctx = transaction.atomic if not dry_run else _NullCtx

        with ctx():
            for alias, canonical in REGION_MAP.items():
                # alias/canonical 비교를 위한 기준 키
                alias_key = _norm(alias, casefold)
                canonical_key = _norm(canonical, casefold)

                # 대상 레코드: region == alias (casefold 옵션 적용)
                if casefold:
                    targets = TrendKeyword.objects.all().only("id", "region", "keyword")
                    targets = [t for t in targets if _norm(t.region, True) == alias_key]
                else:
                    targets = list(
                        TrendKeyword.objects.filter(region=alias).only(
                            "id", "region", "keyword"
                        )
                    )

                if not targets:
                    continue

                for row in targets:
                    old_region = row.region
                    kw = row.keyword

                    # 이미 canonical 이면 스킵
                    if _norm(old_region, casefold) == canonical_key:
                        skipped += 1
                        continue

                    # 이동 대상 (canonical, kw) 가 이미 존재하면 → 중복 병합(현재 레코드 삭제)
                    if (canonical_key, _norm(kw, casefold)) in existing:
                        to_update += 1
                        if verbose_rows:
                            self.stdout.write(
                                f"MERGE: [{old_region}] '{kw}' → [{canonical}] (중복 존재: 삭제)"
                            )
                        merged_deleted += 1
                        if not dry_run:
                            # 실제 삭제
                            TrendKeyword.objects.filter(id=row.id).delete()
                        continue

                    # 존재하지 않으면 → region 을 canonical 로 업데이트
                    to_update += 1
                    if verbose_rows:
                        self.stdout.write(
                            f"UPDATE: [{old_region}] '{kw}' → [{canonical}]"
                        )
                    if not dry_run:
                        row.region = canonical
                        try:
                            row.save(update_fields=["region"])
                        except IntegrityError:
                            # unique_together 적용된 경우 혹시 레이스/경합으로 충돌 시 안전하게 삭제로 폴백
                            TrendKeyword.objects.filter(id=row.id).delete()
                            merged_deleted += 1
                        else:
                            actually_updated += 1
                            # 스냅샷 갱신
                            existing.setdefault(
                                (canonical_key, _norm(kw, casefold)), set()
                            ).add(row.id)
                            # 기존 키에서 제거
                            old_key = (alias_key, _norm(kw, casefold))
                            if old_key in existing and row.id in existing[old_key]:
                                existing[old_key].remove(row.id)

        # 요약 출력
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=== normalize_trend_keywords 결과 ==="))
        self.stdout.write(f"스캔 개수: {scanned}")
        self.stdout.write(f"변경 대상: {to_update}")
        self.stdout.write(
            f"실제 업데이트: {actually_updated}{' (dry-run: 0)' if dry_run else ''}"
        )
        self.stdout.write(
            f"중복 병합(삭제): {merged_deleted}{' (dry-run: 0)' if dry_run else ''}"
        )
        self.stdout.write(f"스킵: {skipped}")
        self.stdout.write(self.style.SUCCESS("완료."))


class _NullCtx:
    """dry-run용 더미 컨텍스트 (with _NullCtx(): pass)"""

    def __enter__(self):  # noqa
        return None

    def __exit__(self, exc_type, exc, tb):  # noqa
        return False
