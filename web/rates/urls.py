from django.urls import path

from . import views

app_name = 'rates'

urlpatterns = [
    path('', views.home, name='home'),
]
