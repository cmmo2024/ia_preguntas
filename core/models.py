# core/models.py

from django.db import models
from django.contrib.auth.models import User
from datetime import timedelta
from django.utils import timezone

class ProfessionalCategory(models.TextChoices):
    MATEMATICAS = 'matematicas', 'Matemáticas'
    FISICA = 'fisica', 'Física'
    QUIMICA = 'quimica', 'Química'
    BIOLOGIA = 'biologia', 'Biología'
    INFORMATICA = 'informatica', 'Informática'
    MEDICINA = 'medicina', 'Medicina'
    OTRO = 'otro', 'Otro'

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    PLAN_CHOICES = (
        ('free', 'Gratuito'),
        ('premium', 'Premium')
    )
    plan = models.CharField(max_length=10, choices=PLAN_CHOICES, default='free')

    # Cuotas por periodo
    daily_ia_requests = models.PositiveIntegerField(default=0)
    daily_exams = models.PositiveIntegerField(default=0)

    # Periodo de validez actual
    period_start = models.DateField(auto_now_add=True)
    period_days = models.PositiveIntegerField(default=30)  # duración del periodo

    # Preferencia Perfil usuario
    category = models.CharField(
        max_length=20,
        choices=ProfessionalCategory.choices,
        default=ProfessionalCategory.OTRO,
        null=True,
        blank=True
    )

    def reset_period_if_needed(self):
        today = timezone.now().date()
        if today > self.period_start + timedelta(days=self.period_days):
            self.daily_ia_requests = 0
            self.daily_exams = 0
            self.period_start = today
            self.save()

    def can_make_request(self):
        self.reset_period_if_needed()
        limit = 20 if self.plan == 'free' else 100 # Cambiar estos valores para modificar Preguntas/Plan
        return self.daily_ia_requests < limit

    def can_take_exam(self):
        self.reset_period_if_needed()
        limit = 20 if self.plan == 'free' else 100 # Cambiar estos valores para modificar Exámenes/Plan
        return self.daily_exams < limit

    def increment_request(self):
        if self.can_make_request():
            self.daily_ia_requests += 1
            self.save()

    def increment_exam(self):
        if self.can_take_exam():
            self.daily_exams += 1
            self.save()
    @property
    def max_daily_requests(self):
        return 5 if self.plan == 'free' else 100

    @property
    def max_daily_exams(self):
        return 5 if self.plan == 'free' else 40

class Subject(models.Model):
    name = models.CharField(max_length=100, verbose_name="Nombre")

    def __str__(self):
        return self.name


class Topic(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, verbose_name="Asignatura")
    name = models.CharField(max_length=100, verbose_name="Nombre")
    description = models.TextField(verbose_name="Descripción", blank=True, null=True)

    def __str__(self):
        return f"{self.subject} - {self.name}"


class Conversation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    topic = models.ForeignKey(Topic, on_delete=models.SET_NULL, null=True)
    question = models.TextField()
    response = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.topic}: {self.question[:30]}..."
    
import jsonfield  # Instala si no lo tienes: pip install jsonfield

class Exam(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    subject_name = models.CharField(max_length=255)
    topic_name = models.CharField(max_length=255)
    questions = jsonfield.JSONField()  # Almacena las preguntas y opciones
    user_answers = jsonfield.JSONField()  # Almacena qué respondió el usuario
    correct_count = models.PositiveIntegerField(default=0)
    total_questions = models.PositiveIntegerField(default=7)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Examen de {self.topic_name} - {self.user.username}"    