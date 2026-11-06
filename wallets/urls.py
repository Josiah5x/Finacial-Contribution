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
    path(
    'my-statement/pdf/',
    views.member_statement_pdf,
    name='member_statement_pdf'
    ),
    path(
    'my-statement',
    views.member_statement,
    name='member_statement'
    ),
    path('my-wallet/', views.member_wallet, name='member_wallet'),
]