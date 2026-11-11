from django.urls import path
from . import views

app_name = 'collections'

urlpatterns = [
    path('', views.collection_list, name='collection_list'),
    path('create/', views.collection_create, name='collection_create'),

    path(
        '<int:pk>/verify/',
        views.collection_verify,
        name='collection_verify',
    ),
    path(
        '<int:pk>/reject/',
        views.collection_reject,
        name='collection_reject',
    ),

     path(
        'paystack/start/',
        views.paystack_start,
        name='paystack_start',
    ),

    path(
        'paystack/callback/',
        views.paystack_callback,
        name='paystack_callback',
    ),

    path(
        'paystack/webhook/',
        views.paystack_webhook,
        name='paystack_webhook',
    ),

    path('<int:pk>/', views.collection_detail, name='collection_detail'),
]