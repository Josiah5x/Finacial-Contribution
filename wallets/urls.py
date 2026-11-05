from django.urls import path
from . import views

app_name = 'wallets'

urlpatterns = [
    path('', views.wallet_list, name='wallet_list'),
    path('<int:pk>/', views.wallet_detail, name='wallet_detail'),
    path(
    'my-transactions/',
    views.member_transactions,
    name='member_transactions'
    ),
]