from django.urls import path
from . import views

app_name = 'expenses'

urlpatterns = [
    path('', views.expense_list, name='expense_list'),
    path('create/', views.expense_create, name='expense_create'),
    path('<int:pk>/', views.expense_detail, name='expense_detail'),

    path('<int:pk>/approve/', views.expense_approve, name='expense_approve'),
    path('<int:pk>/reject/', views.expense_reject, name='expense_reject'),
    path('<int:pk>/pay/', views.expense_pay, name='expense_pay'),

    path('categories/', views.category_list, name='category_list'),
    path('categories/create/', views.category_create, name='category_create'),
]