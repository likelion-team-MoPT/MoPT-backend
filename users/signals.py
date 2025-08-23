# users/signals.py
import os

from django.db.models.signals import post_migrate


# 시드 실행 함수
def _run_seed(sender, app_config=None, **kwargs):
    # 우리 앱(users)에 대해서만 실행
    if app_config and app_config.name != "users":
        return

    # 환경변수로 켜고 끄기 (기본 ON)
    if os.getenv("DJANGO_BOOT_SEED", "1") != "1":
        return

    try:
        from .boot import ensure_seed_users

        ensure_seed_users()  # 반드시 아이템포턴트하게 작성
    except Exception:
        # 부팅/마이그레이션을 막지 않음(원하면 로거로 남기기)
        pass


def connect_post_migrate():
    """
    시그널 중복 연결 방지 + 연결
    """
    dispatch_uid = "users_post_migrate_seed"
    post_migrate.disconnect(_run_seed, sender=None, dispatch_uid=dispatch_uid)
    post_migrate.connect(_run_seed, sender=None, dispatch_uid=dispatch_uid, weak=False)
