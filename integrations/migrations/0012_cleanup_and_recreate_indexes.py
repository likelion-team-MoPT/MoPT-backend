from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        (
            "integrations",
            "0011_alter_posconnection_unique_together_and_more",
        ),  # ← 현재 마지막에 맞춰주세요
    ]

    operations = [
        # 1) 남아있을 수 있는 이전 이름 인덱스/유니크 인덱스 선삭제 (존재해도 안전, 없어도 통과)
        migrations.RunSQL("DROP INDEX IF EXISTS uniq_active_pos_store_per_provider;"),
        migrations.RunSQL("DROP INDEX IF EXISTS pos_prov_store_idx;"),
        # 2) 모델과 맞춘 새 이름으로 생성
        migrations.AddIndex(
            model_name="posconnection",
            index=models.Index(
                fields=["provider", "store_external_id"],
                name="pos_prov_store_idx_v2",
            ),
        ),
        migrations.AddConstraint(
            model_name="posconnection",
            constraint=models.UniqueConstraint(
                fields=["provider", "store_external_id"],
                condition=Q(status="active"),
                name="uniq_active_pos_store_per_provider_v2",
            ),
        ),
    ]
