# core/models.py

from django.db import models
from django.contrib.auth.models import User
from datetime import timedelta
from django.utils import timezone

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

    def reset_period_if_needed(self):
        today = timezone.now().date()
        if today > self.period_start + timedelta(days=self.period_days):
            self.daily_ia_requests = 0
            self.daily_exams = 0
            self.period_start = today
            self.save()

    def can_make_request(self):
        self.reset_period_if_needed()
        limit = 5 if self.plan == 'free' else 100
        return self.daily_ia_requests < limit

    def can_take_exam(self):
        self.reset_period_if_needed()
        limit = 5 if self.plan == 'free' else 40
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