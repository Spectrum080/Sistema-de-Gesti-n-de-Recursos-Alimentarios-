from django.http import request
from django.shortcuts import render

def consultarDonaciones(request):
    donaciones = [
           {
               'id': '001',
               'categoria': 'Granos y Semillas',
               'descripcion': 'Frijol negro en grano',
               'cantidad': '50',
               'unidad': 'Kilogramos (kg)',
               'caducidad': '2026-12-15',
               'conservacion': 'Temperatura ambiente',
               'estado': 'Recibido'
           },
           {
               'id': '002',
               'categoria': 'Lácteos',
               'descripcion': 'Leche entera ultrapasteurizada',
               'cantidad': '120',
               'unidad': 'Litros (L)',
               'caducidad': '2026-11-20',
               'conservacion': 'Refrigeración',
               'estado': 'Pendiente'
           }
       ]
    return render(request, 'alertas/consultarDonaciones.html', {'donaciones': donaciones})

def cargarDonaciones(request):
    return render(request, 'alertas/cargarDonaciones.html')