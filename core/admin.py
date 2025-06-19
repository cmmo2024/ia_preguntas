from django.contrib import admin
from .models import Conversation
from django.contrib.auth.models import User

# Opcional: Puedes personalizar cómo se muestra el modelo
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('user', 'topic', 'question_short', 'created_at')
    list_filter = ('topic', 'user')
    search_fields = ('question', 'response')

    def question_short(self, obj):
        return obj.question[:50] + "..." if len(obj.question) > 50 else obj.question
    question_short.short_description = "Pregunta"

admin.site.register(Conversation, ConversationAdmin)
