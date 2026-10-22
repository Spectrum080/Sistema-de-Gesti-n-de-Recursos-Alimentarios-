from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='users/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('Sing_up/', views.Sing_up, name='Sing_up'),

    path('reset_password/',
        auth_views.PasswordResetView.as_view(template_name='users/reset_password.html'),
        name='reset_password'),
    path('reset_password/enviado/',
         auth_views.PasswordResetDoneView.as_view(template_name='users/reset_done.html'),
         name='password_reset_done'),
    path('reset/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(template_name='users/reset_confirm.html'),
         name='password_reset_confirm'),
    path('reset/completo/',
         auth_views.PasswordResetCompleteView.as_view(template_name='users/reset_complete.html'),
         name='password_reset_complete'),
]