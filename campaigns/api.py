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
    obj = get_object_or_404(Campaign, id=campaign_id)
    return obj


# 3. 캠페인 수정
@router.patch("/{campaign_id}", response=MessageOut)
def update_campaign(request, campaign_id: int, payload: CampaignUpdateIn):
    campaign = get_object_or_404(Campaign, id=campaign_id)

    # Pydantic v2 표준
    update_data = payload.model_dump(exclude_unset=True)

    # duration 처리: start/end와 start_date/end_date 모두 허용
    if "duration" in update_data:
        duration_data = update_data.pop("duration") or {}
        start = duration_data.get("start_date", duration_data.get("start"))
        end = duration_data.get("end_date", duration_data.get("end"))
        if start is not None:
            campaign.start_date = start
        if end is not None:
            campaign.end_date = end

    for attr, value in update_data.items():
        setattr(campaign, attr, value)

    campaign.save()
    return MessageOut(message="캠페인이 성공적으로 수정되었습니다.")


# 4. 캠페인 중단(상태 변경)
@router.patch("/{campaign_id}/status", response=CampaignStatusOut)
def update_campaign_status(request, campaign_id: int, payload: CampaignStatusUpdateIn):
    campaign = get_object_or_404(Campaign, id=campaign_id)

    # Enum 또는 str 모두 허용
    new_status = (
        payload.status.value
        if hasattr(payload.status, "value")
        else str(payload.status)
    )
    campaign.status = new_status
    campaign.save()

    return CampaignStatusOut(
        id=campaign.id,
        name=campaign.name,
        status=campaign.status,
        message=f"캠페인 상태가 '{campaign.status}'(으)로 변경되었습니다.",
    )
