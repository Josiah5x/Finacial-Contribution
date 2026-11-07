from django.urls import path
from . import views

app_name = 'loans'

urlpatterns = [
    path('apply/', views.loan_apply, name='loan_apply'),
    path('my-loans/', views.my_loans, name='my_loans'),

    path('', views.loan_list, name='loan_list'),
    path('<int:pk>/', views.loan_detail, name='loan_detail'),
    path('<int:pk>/approve/', views.loan_approve, name='loan_approve'),
    path('<int:pk>/reject/', views.loan_reject, name='loan_reject'),
]