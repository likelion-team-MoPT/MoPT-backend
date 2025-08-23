# users/boot.py
from django.contrib.auth import get_user_model
from django.db import transaction


def ensure_seed_users():
    """
    여러 번 호출되어도 안전(idempotent)하게 동작하도록 작성.
    """
    User = get_user_model()

    with transaction.atomic():
        # admin 계정
        User.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin@example.com",
                "is_staff": True,
                "is_superuser": True,
            },
        )
        # demo 계정
        User.objects.get_or_create(
            username="demo",
            defaults={
                "email": "demo@example.com",
                "is_staff": False,
                "is_superuser": False,
            },
        )
