from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='users/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('Sing_up/', views.Sing_up, name='Sing_up'),
    
    # Rutas de Dashboard y Roles
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboardDonante/', views.dashboardDonante, name='dashboardDonante'),
    path('dashboardReceptor/', views.dashboardReceptor, name='dashboardReceptor'),
    
    # Configuración e Informes
    path('configuracion/', views.configuracion, name='configuracion'),
    path('exportar-informe/', views.exportar_informe, name='exportarInforme'),

    # Rutas para restablecer contraseña
    path('reset_password/',
        auth_views.PasswordResetView.as_view(template_name='users/reset_password.html'),
        name='reset_password'),
    path('reset_password/enviado/',
        auth_views.PasswordResetDoneView.as_view(template_name='users/reset_done.html'),
        name='password_reset_done'),
]
