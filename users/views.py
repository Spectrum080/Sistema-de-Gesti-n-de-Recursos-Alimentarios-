from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def dashboard(request):
    return render(request, 'users/dashboard.html')

def Sing_up(request):
    return render(request, 'users/Sing_up.html')

def reset_password(request):
    return render(request, 'users/reset_password.html')