from typing import Optional

from django.shortcuts import get_object_or_404
from ninja import Router

from .models import Campaign
from .schemas import (
    CampaignDetailOut,
    CampaignListItemOut,
    CampaignListOut,
    CampaignStatusOut,
    CampaignStatusUpdateIn,
    CampaignUpdateIn,
    MessageOut,
    PaginationMeta,
)

router = Router()


# 1. 캠페인 목록 조회
@router.get("/", response=CampaignListOut)
def list_campaigns(request, status: Optional[str] = None):
    queryset = Campaign.objects.all()

    # status 파라미터가 있고, 그 값이 'all'이 아닐 때만 필터링
    if status and status.lower() != "all":
        queryset = queryset.filter(status=status)

    # 페이지네이션 로직 (간단하게 구현)
    total = queryset.count()
    limit = 10  # 한 페이지에 10개씩
    page = 1  # 현재 1페이지

    # 스키마에 맞게 데이터 가공
    items = [
        CampaignListItemOut.model_validate(c, from_attributes=True) for c in queryset
    ]

    return CampaignListOut(
        data=items, meta=PaginationMeta(page=page, limit=limit, total=total)
    )


# 2. 캠페인 상세 조회
@router.get("/{campaign_id}", response=CampaignDetailOut)
def get_campaign(request, campaign_id: int):
    campaign = get_object_or_404(Campaign, id=campaign_id)
    return CampaignDetailOut.model_validate(campaign, from_attributes=True)


# 3. 캠페인 수정
@router.patch("/{campaign_id}", response=MessageOut)
def update_campaign(request, campaign_id: int, payload: CampaignUpdateIn):
    campaign = get_object_or_404(Campaign, id=campaign_id)

    update_data = payload.dict(exclude_unset=True)

    # duration 같은 특별한 필드 처리
    if "duration" in update_data:
        duration_data = update_data.pop("duration")
        if "start" in duration_data:
            campaign.start_date = duration_data["start"]
        if "end" in duration_data:
            campaign.end_date = duration_data["end"]

    for attr, value in update_data.items():
        setattr(campaign, attr, value)

    campaign.save()
    return MessageOut(message="캠페인이 성공적으로 수정되었습니다.")


# 4. 캠페인 중단(상태 변경)
@router.patch("/{campaign_id}/status", response=CampaignStatusOut)
def update_campaign_status(request, campaign_id: int, payload: CampaignStatusUpdateIn):
    campaign = get_object_or_404(Campaign, id=campaign_id)
    campaign.status = payload.status
    campaign.save()

    return CampaignStatusOut(
        id=campaign.id,
        name=campaign.name,
        status=campaign.status,
        message=f"캠페인 상태가 '{campaign.status}'(으)로 변경되었습니다.",
    )
