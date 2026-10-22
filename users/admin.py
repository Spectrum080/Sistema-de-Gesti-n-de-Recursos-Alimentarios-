from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario, Donante, Receptor, Administrador

admin.site.register(Usuario, UserAdmin)
admin.site.register(Donante)
admin.site.register(Receptor)
admin.site.register(Administrador)