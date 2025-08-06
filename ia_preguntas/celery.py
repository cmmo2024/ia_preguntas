# ia_preguntas/celery.py
import os
from celery import Celery
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ia_preguntas.settings')

app = Celery('ia_preguntas')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Opcional: prueba de conexión
@app.task
def test_task():
    print("Tarea de prueba ejecutada")