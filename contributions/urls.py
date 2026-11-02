from django.urls import path
from . import views

app_name = 'contributions'

urlpatterns = [
    # Enrolments
    path('enrollments/', views.enrollment_list, name='enrollment_list'),
    path('enrollments/create/', views.enrollment_create, name='enrollment_create'),
    path('enrollments/<int:pk>/', views.enrollment_detail, name='enrollment_detail'),
    path(
        'enrollments/<int:pk>/cancel/',
        views.enrollment_cancel,
        name='enrollment_cancel'
    ),

    # Contribution plans
    path('', views.plan_list, name='plan_list'),
    path('create/', views.plan_create, name='plan_create'),
    path('<int:pk>/', views.plan_detail, name='plan_detail'),
    path('<int:pk>/edit/', views.plan_update, name='plan_update'),
    path('<int:pk>/toggle-status/', views.plan_toggle_status, name='plan_toggle_status'),
]