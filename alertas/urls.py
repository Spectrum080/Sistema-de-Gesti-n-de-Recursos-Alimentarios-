from django.urls import path
from django.contrib.auth import admin, views as auth_views
from . import views

urlpatterns = [
    path('consultarDonaciones', views.consultarDonaciones, name='consultarDonaciones'),
]