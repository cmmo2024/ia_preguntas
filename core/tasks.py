# core/tasks.py
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

@shared_task
def send_weekly_performance_email():
    """
    Envía un email semanal a todos los usuarios con bajo rendimiento
    """
    subject = "📊 Tu resumen semanal de rendimiento"
    from_email = settings.DEFAULT_FROM_EMAIL or 'no-reply@tuapp.com'

    for user in User.objects.filter(is_active=True):
        # Solo si tiene perfil y ha hecho exámenes
        try:
            profile = user.userprofile
        except:
            continue

        # Reutilizamos la función que ya tienes
        weak_areas = profile.get_low_performance_areas(min_score=70, days=14)

        if not weak_areas:
            continue  # No enviar si no hay áreas débiles

        # Calcular promedio general
        exams = profile.user.exam_set.all()
        total_questions = sum(e.total_questions for e in exams)
        correct_answers = sum(e.correct_count for e in exams)
        avg = round(correct_answers / total_questions * 100, 1) if total_questions else 0

        # Construir mensaje
        topics_list = "\n".join([
            f"• {area['name']}: {area['score']}% de aciertos" for area in weak_areas
        ])

        message = f"""
Hola {user.first_name or user.username},

Este es tu resumen semanal de rendimiento en la plataforma:

📊 **Promedio general**: {avg}%
🔴 **Temas para repasar**:
{topics_list}

💡 Recomendación: Haz un examen en estos temas para mejorar tu comprensión.

¡Sigue así! Cada intento te acerca más a tu meta.

Saludos,
Tu equipo de aprendizaje
        """.strip()

        # Enviar email
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=from_email,
                recipient_list=[user.email],
                fail_silently=False,
            )
            print(f"Email enviado a {user.email}")
        except Exception as e:
            print(f"Error enviando email a {user.email}: {e}")