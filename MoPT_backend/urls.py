"""MoPT_backend URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path
from ninja import NinjaAPI

from ai_insights.api import router as insights_router
from campaigns.api import router as campaigns_router
from home.api import router as home_router
from integrations.api import router as integrations_router
from reports.api import router as reports_router
from users.api import router as users_router  # 최소 router 하나

api = NinjaAPI(title="MoPT API", version="1.0")

api.add_router("/insights", insights_router)
api.add_router("/campaigns", campaigns_router)
api.add_router("/home", home_router)
api.add_router("/reports", reports_router)
api.add_router("/users", users_router)
api.add_router("/integrations", integrations_router)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", api.urls),
]
