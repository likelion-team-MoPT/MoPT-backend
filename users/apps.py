from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "users"

    def ready(self):
        # post_migrate 시그널 연결만 담당
        from .signals import connect_post_migrate

        connect_post_migrate()

        # 마이그레이션/관리 명령 중엔 건너뛰기(원하면 제거 가능)
        import sys

        mgmt_cmds = {"makemigrations", "migrate", "collectstatic", "test"}
        if any(cmd in sys.argv for cmd in mgmt_cmds):
            return

        try:
            from .boot import ensure_seed_users

            ensure_seed_users()
        except Exception:
            # 부팅이 막히지 않도록 무조건 삼켜줌(로그만 남기고 싶으면 print/LOGGER)
            pass
