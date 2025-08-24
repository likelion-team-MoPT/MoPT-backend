from decimal import Decimal
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
def list_campaigns(
    request, status: Optional[str] = None, page: int = 1, limit: int = 10
):
    qs = Campaign.objects.all()
    if status and status.lower() != "all":
        qs = qs.filter(status__iexact=status)

    total = qs.count()
    offset = max(page, 1) - 1
    offset *= limit

    # 원시 값만 뽑아서 안전 변환(Decimal NaN/Inf, None 등 처리)
    rows = list(
        qs.order_by("-created_at").values(
            "id", "name", "channel", "status", "roas", "spend", "start_date", "end_date"
        )[offset : offset + limit]
    )

    norm = []
    for r in rows:
        roas = r.get("roas")
        if isinstance(roas, Decimal):
            roas = float(roas) if roas.is_finite() else None

        spend = r.get("spend")
        if isinstance(spend, Decimal):
            spend = float(spend) if spend.is_finite() else None

        norm.append(
            {
                "id": r["id"],
                "name": r.get("name") or "",
                "channel": r.get("channel"),
                "status": r.get("status"),
                "roas": roas,
                "spend": spend,
                "start_date": r.get("start_date"),
                "end_date": r.get("end_date"),
            }
        )

    items = [CampaignListItemOut(**n) for n in norm]
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
