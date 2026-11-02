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

    path('<int:pk>/', views.collection_detail, name='collection_detail'),
]