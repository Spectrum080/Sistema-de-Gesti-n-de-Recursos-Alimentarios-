from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Donacion

@login_required
def subir_donacion(request):
    if request.method == 'POST':
        titulo = request.POST.get('titulo')
        tipo = request.POST.get('tipo')
        cantidad = request.POST.get('cantidad')
        fecha_caducidad = request.POST.get('fecha_caducidad')
        descripcion = request.POST.get('descripcion')

        Donacion.objects.create(
            donante=request.user,
            titulo=titulo,
            tipo=tipo,
            cantidad=cantidad,
            fecha_caducidad=fecha_caducidad,
            descripcion=descripcion
        )
        return redirect('subir_donacion')

    return render(request, 'donaciones/subir_donacion.html')