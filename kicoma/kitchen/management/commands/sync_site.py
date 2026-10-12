from django.conf import settings
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Update the current Site used in account emails from tenant settings."

    def handle(self, *args, **options):
        if not settings.DJANGO_SITE_DOMAIN:
            self.stdout.write("DJANGO_SITE_DOMAIN not configured; Site unchanged.")
            return

        site, _created = Site.objects.update_or_create(
            pk=settings.SITE_ID,
            defaults={
                "domain": settings.DJANGO_SITE_DOMAIN,
                "name": settings.DJANGO_SITE_NAME,
            },
        )
        Site.objects.clear_cache()
        self.stdout.write(f"Site configured: {site.name} ({site.domain})")
