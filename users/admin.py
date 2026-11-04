from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario, Donante, Receptor, Administrador

# Registro de perfiles de usuario y roles dentro del panel de administración
admin.site.register(Usuario, UserAdmin)
admin.site.register(Donante)
admin.site.register(Receptor)
admin.site.register(Administrador)
