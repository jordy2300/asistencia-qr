from django.apps import AppConfig

class AsistenciaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'asistencia'

    def ready(self):
        import os
        try:
            from django.contrib.auth.models import User
            admin_user = os.environ.get('ADMIN_USER', '')
            admin_pass = os.environ.get('ADMIN_PASSWORD', '')
            if admin_user and admin_pass:
                if not User.objects.filter(username=admin_user).exists():
                    User.objects.create_superuser(admin_user, '', admin_pass)
        except Exception:
            pass