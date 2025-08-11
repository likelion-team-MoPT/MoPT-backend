from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
from .models import Insight
from .serializers import InsightSerializer

class CustomPagination(PageNumberPagination):
    page_size_query_param = 'limit'

    def get_paginated_response(self, data):
        return Response({
            'data': data,
            'meta': {
                'page': self.page.number,
                'limit': self.page.paginator.per_page,
                'total': self.page.paginator.count,
            }
        })

class InsightListView(APIView):
    def get(self, request):
        insights = Insight.objects.order_by('-created_at')
        paginator = CustomPagination()
        page = paginator.paginate_queryset(insights, request)
        serializer = InsightSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)
