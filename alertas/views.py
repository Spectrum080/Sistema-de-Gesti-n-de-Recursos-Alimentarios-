from django.http import request
from django.shortcuts import render

def consultarDonaciones(request):
    return render(request, 'alertas/consultarDonaciones.html')