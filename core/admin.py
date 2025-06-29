from django.contrib import admin
from .models import Subject, Topic, Conversation

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