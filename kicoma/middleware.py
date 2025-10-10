from django.contrib import messages
from django.http import HttpResponse

from kicoma.kitchen import daily_job


class HealthCheckMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == "/health-check/":
            response = HttpResponse("OK")
        else:
            response = self.get_response(request)

        return response


class DailyJobMiddleware:
    """Runs the daily job once per day and attaches messages to requests."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and daily_job.should_run_today():
            daily_job.run_daily_job()

        message_data = daily_job.get_message()
        if message_data:
            messages.add_message(request, message_data["level"], message_data["text"], extra_tags=message_data["tag"])
            request.daily_job_message = daily_job.get_message()

        return self.get_response(request)
