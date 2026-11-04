
from django.urls import path
from . import views

app_name = 'withdrawals'

urlpatterns = [
    path('', views.withdrawal_list, name='withdrawal_list'),
    path('create/', views.withdrawal_create, name='withdrawal_create'),
    path('<int:pk>/', views.withdrawal_detail, name='withdrawal_detail'),
    path('<int:pk>/approve/', views.withdrawal_approve, name='withdrawal_approve'),
    path('<int:pk>/reject/', views.withdrawal_reject, name='withdrawal_reject'),
    path('<int:pk>/pay/', views.withdrawal_pay, name='withdrawal_pay'),
]
