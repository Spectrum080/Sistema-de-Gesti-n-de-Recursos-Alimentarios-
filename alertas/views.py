from django.http import request
from django.shortcuts import render

def consultarDonaciones(request):
    donaciones = [
        {
            'ID': '001',
            'donante': 'Banco de Alimentos Regional',
            'alimento': 'Despensas básicas',
            'cantidad': '30 cajas',
            'tipo': 'No perecedero',
            'estado': 'Recibido'
        },
        {
            'ID': '002',
            'donante': 'Supermercado Central',
            'alimento': 'Enlatados y Leche',
            'cantidad': '80 unidades',
            'tipo': 'No perecedero',
            'estado': 'Pendiente'
        }
    ]
    return render(request, 'alertas/consultarDonaciones.html', {'donaciones': donaciones})

def cargarDonaciones(request):
    return render(request, 'alertas/cargarDonaciones.html')