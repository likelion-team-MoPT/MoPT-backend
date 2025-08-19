# reports/migrations/000X_seed_daily_performances.py

import random
from datetime import timedelta

from django.db import migrations


def create_initial_daily_performances(apps, schema_editor):
    """
    모든 캠페인에 대해 캠페인 기간 전체에 해당하는 일별 데이터를 생성합니다.
    """
    Campaign = apps.get_model("campaigns", "Campaign")
    DailyPerformance = apps.get_model("reports", "DailyPerformance")

    # DB에 있는 모든 캠페인을 가져옵니다.
    all_campaigns = Campaign.objects.all()
    daily_performances_to_create = []

    for campaign in all_campaigns:
        # 캠페인 기간 동안 하루씩 반복
        current_date = campaign.start_date
        while current_date <= campaign.end_date:
            # 랜덤하지만 그럴듯한 일별 데이터 생성
            spend = (
                campaign.spend // (campaign.end_date - campaign.start_date).days
                if (campaign.end_date - campaign.start_date).days > 0
                else campaign.spend
            )
            sales = (
                campaign.sales // (campaign.end_date - campaign.start_date).days
                if (campaign.end_date - campaign.start_date).days > 0
                else campaign.sales
            )

            daily_spend = spend + random.randint(-int(spend * 0.3), int(spend * 0.3))
            daily_sales = sales + random.randint(-int(sales * 0.3), int(sales * 0.3))

            daily_performance = DailyPerformance(
                campaign=campaign,
                date=current_date,
                spend=max(0, daily_spend),  # 0보다 작아지지 않도록 보정
                sales=max(0, daily_sales),
            )
            daily_performances_to_create.append(daily_performance)

            current_date += timedelta(days=1)

    DailyPerformance.objects.bulk_create(daily_performances_to_create)


def remove_initial_daily_performances(apps, schema_editor):
    """데이터 롤백 시 모든 일별 데이터를 삭제합니다."""
    DailyPerformance = apps.get_model("reports", "DailyPerformance")
    DailyPerformance.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("reports", "0001_initial"),
        (
            "campaigns",
            "0002_seed_campaigns",
        ),  # 여러분의 최신 캠페인 마이그레이션 파일 이름
    ]
    operations = [
        migrations.RunPython(create_initial_daily_performances),
    ]
