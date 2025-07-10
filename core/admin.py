from django.contrib import admin
from django.contrib.auth.models import User
from .models import Subject, Topic, Conversation, UserProfile

# Registro básico del modelo UserProfile
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'daily_ia_requests', 'daily_exams', 'period_start', 'period_days')
    search_fields = ('user__username',)
    list_filter = ('plan',)
    raw_id_fields = ('user',)  # Mejora la selección de usuarios en grandes bases de datos


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
    list_display = ('name',)
    search_fields = ('name',)
    ordering = ('name',)

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