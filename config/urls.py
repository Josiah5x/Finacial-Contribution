from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    path('', include('core.urls')),
    path('accounts/', include('accounts.urls')),
    path('members/', include('members.urls')),
    path('agents/', include('agents.urls')),
    path('contributions/', include('contributions.urls')),
    path('collections', include('collections_daily.urls')),
    path('wallets/', include('wallets.urls')),
    path('withdrawals/', include('withdrawals.urls')),
    path('expenses/', include('expenses.urls')),
    path('reports/', include('reports.urls')),
    path('loans/', include('loans.urls')),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )