# core/models.py

from django.db import models
from django.contrib.auth.models import User
from datetime import timedelta
from django.utils import timezone
#import jsonfield

 # --------Planes-------------------------------------------------------------------------
from django.core.validators import MinValueValidator

class PlanConfig(models.Model):
    plan = models.CharField(
        max_length=10,
        choices=[
            ('free', 'Gratis'),
            ('premium', 'Premium')
        ],
        unique=True
    )
    daily_requests = models.PositiveIntegerField(
        default=3,
        verbose_name="Peticiones diarias (Free)"
    )
    total_requests = models.PositiveIntegerField(
        default=300,
        verbose_name="Peticiones totales (Premium)"
    )
    price_cup = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=500.00,
        verbose_name="Precio del plan Premium (CUP)"
    )
    duration_days = models.PositiveIntegerField(
        default=30,
        verbose_name="Duración del plan (días)"
    )

    def __str__(self):
        return f"Configuración de plan: {self.get_plan_display()}"

    @classmethod
    def get_config(cls, plan_name):
        """Devuelve la configuración del plan o valores por defecto"""
        try:
            return cls.objects.get(plan=plan_name)
        except cls.DoesNotExist:
            # Valores por defecto
            return cls(
                plan=plan_name,
                daily_requests=3 if plan_name == 'free' else 0,
                total_requests=300 if plan_name == 'premium' else 0,
                price_cup=500.00 if plan_name == 'premium' else 0.00,
                duration_days=30
            )

# UCategoria Profexional---Para el perfil de usuario-----------------------------
class ProfessionalCategory(models.TextChoices):
    MATEMATICAS = 'matematicas', 'Matemáticas'
    FISICA = 'fisica', 'Física'
    QUIMICA = 'quimica', 'Química'
    BIOLOGIA = 'biologia', 'Biología'
    INFORMATICA = 'informatica', 'Informática'
    MEDICINA = 'medicina', 'Medicina'
    OTRO = 'otro', 'Otro'

# UserProfile---Herada de User de la plataforma-------------------------------
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    plan = models.CharField(
        max_length=10,
        choices=[
            ('free', 'Gratis'),
            ('premium', 'Premium')
        ],
        default='free'
    )
    # Cuotas de uso
    daily_requests = models.PositiveIntegerField(default=0)
    total_requests = models.PositiveIntegerField(default=0)
    # Fecha de inicio del plan
    period_start = models.DateField(auto_now_add=True)
    # Si el plan termina, se borra la cuota total y se reinicia a free
    def reset_to_free(self):
        self.plan = 'free'
        self.total_requests = 0
        self.save()

    def reset_daily(self):
        today = timezone.now().date()
        if today != self.period_start:
            self.daily_requests = 0
            self.period_start = today
            self.save()

    def can_make_request(self):
        self.reset_daily()  # Reinicia cuota diaria si es otro día
        config = PlanConfig.get_config(self.plan)
        if self.plan == 'free':
            return self.daily_requests < config.daily_requests
        elif self.plan == 'premium':
            if self.total_requests >= config.total_requests:
                self.reset_to_free()  # 👈 Aquí se llama al método
                return False
            return self.total_requests < config.total_requests
        return False

    def increment_request(self):
        self.reset_daily()
        if self.plan == 'free':
            self.daily_requests += 1
        elif self.plan == 'premium':
            self.total_requests += 1
            if self.total_requests >= self.plan_config.total_requests:
                self.reset_to_free()
        self.save()

    def reset_period_if_needed(self):
        today = timezone.now().date()
        if self.plan == 'free' and today != self.period_start:
            self.daily_requests = 0
            self.period_start = today
            self.save()
        elif self.plan == 'premium':
            config = self.plan_config
            if self.total_requests >= config.total_requests:
                self.reset_to_free()

    def has_reached_limit(self):
        return not self.can_make_request()
    
    @property
    def plan_config(self):
        from .models import PlanConfig
        try:
            return PlanConfig.objects.get(plan=self.plan)
        except PlanConfig.DoesNotExist:
            # Devuelve valores por defecto si no existe la configuración
            from django.utils import timezone
            return type('obj', (object,), {
                'daily_requests': 3 if self.plan == 'free' else 0,
                'total_requests': 300 if self.plan == 'premium' else 0,
                'period_days': 30,
                'price_cup': 500.00 if self.plan == 'premium' else 0.00
            })

# --------Asignaturas-------------------------------------------------------------------------

class Subject(models.Model):
    name = models.CharField(max_length=100, verbose_name="Nombre")
    # Si user es None → es pública (solo admins pueden crearlas)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Usuario dueño")
    is_public = models.BooleanField(default=True, verbose_name="¿Es pública?")

    class Meta:
        unique_together = ('name', 'user')  # Evita duplicados para el mismo usuario

    def first_topic(self):
        return self.topic_set.first()

    def __str__(self):
        owner = "Pública" if self.is_public else f"de {self.user.username}"
        return f"{self.name} ({owner})"

# --------Temas: Muchos a Uno con Subject------------------------------------------------------
class Topic(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, verbose_name="Asignatura")
    name = models.CharField(max_length=100, verbose_name="Nombre")
    description = models.TextField(verbose_name="Descripción", blank=True, null=True)

    class Meta:
        unique_together = ('name', 'subject')

    def __str__(self):
        return f"{self.subject} - {self.name}"

# --------Conversaciones: Muchas a Uno con User y Topic------------------------------------------
class Conversation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    topic = models.ForeignKey(Topic, on_delete=models.SET_NULL, null=True)
    question = models.TextField()
    response = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.topic}: {self.question[:30]}..."
    

# --------CExámenes: Muchas a Uno con User y Topic------------------------------------------
class Exam(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    subject_name = models.CharField(max_length=255)
    topic_name = models.CharField(max_length=255)
    questions = models.JSONField()  # Almacena las preguntas y opciones
    user_answers = models.JSONField()  # Almacena qué respondió el usuario
    correct_count = models.PositiveIntegerField(default=0)
    total_questions = models.PositiveIntegerField(default=7)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Examen de {self.topic_name} - {self.user.username}"    
    
