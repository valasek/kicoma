from django.shortcuts import render


def landing_page(request):
    return render(request, 'common/home.html')
