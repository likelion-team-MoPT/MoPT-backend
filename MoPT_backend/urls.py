from django.contrib import admin
from django.urls import include, path
from ninja import NinjaAPI

from ai_insights.api import router as insights_router
from campaigns.api import router as campaigns_router
from home.api import router as home_router
from integrations.api import router as integrations_router
from reports.api import router as reports_router
from users.api import router as users_router

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
    path("api/", include("MoPT_backend.urls_legacy")),
]
