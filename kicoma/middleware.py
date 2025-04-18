from django.http import HttpResponse

class HealthCheckMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == "/health-check/":
            # Or perform any "real" health checking, if needed
            response = HttpResponse("OK")
        else:
            response = self.get_response(request)

        return response
