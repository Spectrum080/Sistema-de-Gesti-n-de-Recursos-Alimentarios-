from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Usuario, Donante, Receptor

@login_required
def dashboard(request):
    context = {
        'total_donaciones': 2,
        'peso_total': '35 KG',
        'estatus': 'ACTIVO',
    }
    return render(request, 'users/dashboard.html')

def Sing_up(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        confirm = request.POST['confirm_password']
        tipo = request.POST['UserTypes']

        if password != confirm:
            messages.error(request, 'Las contraseñas no coinciden')
            return render(request, 'users/Sing_up.html')

        if Usuario.objects.filter(username=username).exists():
            messages.error(request, 'Ese usuario ya existe')
            return render(request, 'users/Sing_up.html')

        Modelo = Donante if tipo == 'Donante' else Receptor
        user = Modelo(username=username, email=email)
        user.set_password(password)
        user.save()

        return redirect('login')

    return render(request, 'users/Sing_up.html')

def reset_password(request):
    return render(request, 'users/reset_password.html')