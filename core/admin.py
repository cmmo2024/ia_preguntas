from django.contrib import admin
from django.contrib.auth.models import User
from .models import Subject, Topic, Conversation, UserProfile, PlanConfig, Exam

@admin.register(PlanConfig)
class PlanConfigAdmin(admin.ModelAdmin):
    list_display = ('plan', 'daily_requests', 'total_requests', 'price_cup', 'duration_days')
    list_editable = ('daily_requests', 'total_requests', 'price_cup', 'duration_days')
    readonly_fields = ('plan',)  # Evita cambiar el plan manualmente

# Registro básico del modelo UserProfile
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'daily_requests', 'total_requests', 'period_start')
    search_fields = ('user__username',)
    list_filter = ('plan',)
    raw_id_fields = ('user',)  # Mejora la selección de usuarios en grandes bases de datos

# Registro básico del modelo Exam
@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ('user', 'subject_name', 'topic_name', 'total_questions', 'correct_count', 'created_at')
    list_filter = ('created_at', 'user', 'subject_name')
    search_fields = ('subject_name', 'topic_name', 'user__username')
    readonly_fields = ('created_at',)

# Opcional: Mostrar UserProfile dentro del admin de User
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Perfil'


# Extender el UserAdmin para incluir el inline
class CustomUserAdmin(admin.ModelAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff')


# Re-registrar User con el nuevo admin
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'is_public')
    list_filter = ('is_public', 'user')
    search_fields = ('name', 'user__username')
    ordering = ('name',)
    raw_id_fields = ('user',)

@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ('name', 'subject')
    list_filter = ('subject',)
    search_fields = ('name',)
    ordering = ('subject', 'name')

class ConversationAdmin(admin.ModelAdmin):
    list_display = ('user', 'topic', 'question_short', 'created_at')
    list_filter = ('topic__subject', 'topic', 'user')
    search_fields = ('question', 'response')
    readonly_fields = ('created_at',)

    def question_short(self, obj):
        return obj.question[:50] + "..." if len(obj.question) > 50 else obj.question
    question_short.short_description = "Pregunta"

admin.site.register(Conversation, ConversationAdmin)