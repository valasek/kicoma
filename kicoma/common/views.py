from django.conf import settings
from django.shortcuts import redirect, render


def landing_page(request):
    # The marketing landing page belongs to the demo instance only.
    if not settings.KICOMA_DEMO_MODE:
        return redirect('kitchen:about')
    return render(request, 'common/home.html')
