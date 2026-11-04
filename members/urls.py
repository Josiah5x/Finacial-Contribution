from django.urls import path
from . import views

app_name = 'members'

urlpatterns = [
    path('', views.member_list, name='member_list'),
    path('create/', views.member_create, name='member_create'),

    path('assignments/create/', views.assignment_create, name='assignment_create'),
    path('assignments/<int:pk>/transfer/', views.assignment_transfer, name='assignment_transfer'),

    path('<int:pk>/assignment-history/', views.assignment_history, name='assignment_history'),

    path('<int:pk>/approve/', views.member_approve, name='member_approve'),
    path('<int:pk>/suspend/', views.member_suspend, name='member_suspend'),
    path('<int:pk>/reactivate/', views.member_reactivate, name='member_reactivate'),

    path('<int:pk>/edit/', views.member_update, name='member_update'),
    path('<int:pk>/', views.member_detail, name='member_detail'),
]