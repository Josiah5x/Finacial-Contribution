from django.urls import path
from . import views

app_name = 'agents'

urlpatterns = [
    path('', views.agent_list, name='agent_list'),
    path('create/', views.agent_create, name='agent_create'),
    path('my-members/', views.my_members, name='my_members'),
    

    path('<int:pk>/', views.agent_detail, name='agent_detail'),
    path('<int:pk>/edit/', views.agent_update, name='agent_update'),
    path(
    'promote-member/<int:pk>/', views.promote_member, name='promote_member' ),

    path('<int:pk>/deactivate/', views.agent_deactivate, name='agent_deactivate'),
    path('<int:pk>/activate/', views.agent_activate, name='agent_activate'),
]