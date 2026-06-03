from django.apps import AppConfig

class AsistenciaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'asistencia'

    def ready(self):
        from django.conf import settings
        if not settings.DEBUG:
            return
        try:
            from django.contrib.auth.models import User
            if settings.ADMIN_USER and not User.objects.filter(username=settings.ADMIN_USER).exists():
                User.objects.create_superuser(settings.ADMIN_USER, '', settings.ADMIN_PASSWORD)
        except Exception:
            pass