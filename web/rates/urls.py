from django.urls import path

from . import views

app_name = 'rates'

urlpatterns = [
    path('', views.home, name='home'),
    path('api/dashboard/', views.dashboard_api, name='dashboard_api'),
    path('miniapp/auth/', views.miniapp_auth, name='miniapp_auth'),
    path('miniapp/status/', views.miniapp_status, name='miniapp_status'),
]
