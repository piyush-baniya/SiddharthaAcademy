# ResultManagement/apps.py
from django.apps import AppConfig

class ResultmanagementConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ResultManagement'
    verbose_name = 'Result Management'

    def ready(self):
        import ResultManagement.signals