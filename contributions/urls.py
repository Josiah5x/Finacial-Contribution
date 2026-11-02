from django.urls import path
from . import views

app_name = 'contributions'

urlpatterns = [
    path('', views.plan_list, name='plan_list'),
    path('create/', views.plan_create, name='plan_create'),
    path('<int:pk>/', views.plan_detail, name='plan_detail'),
    path('<int:pk>/edit/', views.plan_update, name='plan_update'),
    path(
        '<int:pk>/toggle-status/',
        views.plan_toggle_status,
        name='plan_toggle_status'
    ),
]