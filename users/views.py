from django.shortcuts import render

# Create your views here.
import json
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods


@require_http_methods(["GET"])
#1.상세프로필조회
def get_profile(request):
    return JsonResponse({
        "nickname": "해커톤참가자",
        "email": "hacker@example.com",
        "phone_number": "010-1234-5678",
        "birthdate": "2000-01-01"
    })

#4. 연동목록조회
def get_integrations(request):
    integrations=[
    {
        "integration_id": "integration-123",
        "provider": "google",
        "connected_at": "2025-07-30T10:00:00Z"
    },
    {
        "integration_id": "integration-456",
        "provider": "kakao",
        "connected_at": "2025-07-29T15:30:00Z"
    },
    {
        "integration_id": "integration-789",
        "provider": "포스기_브랜드명",
        "connected_at": "2025-07-28T11:20:00Z"
    }]
    return JsonResponse(integrations, safe=False)

#6. 현재알림설정값조회
def get_notifications(request):
    return JsonResponse({
        "marketing_alerts": True,
        "activity_notifications": False
    })

#8. 현재 요금제 조회
def get_subscription(request):
    return JsonResponse({
        "plan_name": "베이직 플랜",
        "monthly_price": 29900,
        "currency": "KRW",
        "next_payment_date": "2025-08-15"
})

#9. 결제 카드 목록 조회
def get_payment_methods(request):
    payment_methods=[
    {
        "method_id": "pm-123",
        "card_type": "Visa",
        "masked_number": "**** **** **** 1234",
        "is_default": True
    },
    {
        "method_id": "pm-456",
        "card_type": "Mastercard",
        "masked_number": "**** **** **** 5678",
        "is_default": False
    }]
    return JsonResponse(payment_methods, safe=False)

#10. 결제 내역 조회
def get_billing_history(request):
    billing_history=[
    {
        "invoice_id": "inv-20250715",
        "payment_date": "2025-07-15",
        "amount": 29900,
        "plan_name": "베이직 플랜"
    },
    {
        "invoice_id": "inv-20250615",
        "payment_date": "2025-06-15",
        "amount": 29900,
        "plan_name": "베이직 플랜"
    }]
    return JsonResponse(billing_history, safe=False)

#11. 공지사항 목록 조회
#이 부분 잘 모르겠음음
def get_notices(request):
    page=int(request.GET.get("page", 1))
    limit=int(request.GET.get("limit",6))
    all_notices = [
    {
        "id": "ntc_20250801",
        "title": "8월 정기 점검 안내",
        "created_at": "2025-08-01"
    },
    {
        "id": "ntc_20250725",
        "title": "서비스 기능 업데이트 안내",
        "created_at": "2025-07-25"
    },
    {
        "id": "ntc_20250715",
        "title": "개인정보처리방침 개정 사전 안내",
        "created_at": "2025-07-15"
    },
    {
        "id": "ntc_20250701",
        "title": "7월 정기 점검 안내",
        "created_at": "2025-07-01"
    },
    {
        "id": "ntc_20250601",
        "title": "6월 정기 점검 안내",
        "created_at": "2025-06-01"
    },
    {
        "id": "ntc_20250501",
        "title": "5월 정기 점검 안내",
        "created_at": "2025-05-01"
    }]
    start=(page-1)*limit
    end=start+limit
    notices=all_notices[start:end]
    meta= {
    "page": page,
    "limit": limit,
    "total": len(all_notices),
    } 
    return JsonResponse({
        "data" : notices, "meta" : meta
    })

# 12. 공지사항 세부 목록 조회
def get_notice_detail(request, notice_id):
    notice_detail ={
        "id": notice_id,
        "title": "8월 정기 점검 안내",
        "content": "안녕하세요, 8월 10일 새벽 1시부터 3시까지 시스템 정기 점검이 예정되어 있습니다. 해당 시간 동안 일부 기능이 제한될 수 있으니 양해 부탁드립니다.",
        "created_at": "2025-08-01T09:00:00+09:00"
    }
    return JsonResponse(notice_detail)





@require_http_methods(["PATCH"])
#2. 프로필수정
def update_profile(request):
    try:
        data = json.loads(request.body)
        nickname=data.get("nickname", "새로운닉네임")
        profile_image = data.get("profileImage", "https://your-server.com/image.png")
        
        return JsonResponse({
            "nickname": nickname,
            "email": "hacker@example.com",
            "phone_number": "010-1234-5678",
            "profileImage": profile_image,
            "birthdate": "2000-01-01"
        })
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
#3. 비밀번호변경
def change_password(request):
    try:
        data = json.loads(request.body)
        current_password=data.get("current_password")
        new_password = data.get("new_password")
        #실제비번이 password1234라 가정
        #왜 new_password는 사용안함..?
        actual_password="password1234"

        if current_password!=actual_password:
            return JsonResponse(
                {"message": "현재 비밀번호가 일치하지 않습니다."},
                status=400
            )
        
        # 비밀번호 변경 로직 생략 (현재는 저장하지 않음)
        return HttpResponse(status=204)

    except json.JSONDecodeError:
        return JsonResponse({"message": "Invalid JSON"}, status=400)
    


@require_http_methods(["DELETE"])
#5. 연동해제
def delete_integration(request, integration_id):
    integrations=[
    {
        "integration_id": "integration-123",
        "provider": "google",
        "connected_at": "2025-07-30T10:00:00Z"
    },
    {
        "integration_id": "integration-456",
        "provider": "kakao",
        "connected_at": "2025-07-29T15:30:00Z"
    },
    {
        "integration_id": "integration-789",
        "provider": "포스기_브랜드명",
        "connected_at": "2025-07-28T11:20:00Z"
    }]
    
    updated_integrations=[
        item for item in integrations if item["integration_id"] !=integration_id
    ]
    return JsonResponse(updated_integrations, safe=False)


@require_http_methods(["PUT"])
#7. 알림설정값수정
#put말고 patch로 하면 안됨??
def update_notifications(request):
    try:
        data = json.loads(request.body)
        marketing_alerts=data.get("marketing_alerts", True)
        activity_notifications = data.get("activity_notifications", True)
        
        return JsonResponse({
            "marketing_alerts": marketing_alerts,
            "activity_notifications": activity_notifications
        })
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

