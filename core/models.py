from django.db import models
from django.contrib.auth.models import User

TOPICS = (
    ('ciencia', 'Ciencia'),
    ('tecnologia', 'Tecnología'),
    ('historia', 'Historia'),
    ('cultura', 'Cultura'),
    ('otros', 'Otros')
)

class Conversation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    topic = models.CharField(max_length=20, choices=TOPICS)
    question = models.TextField()
    response = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.topic}: {self.question[:30]}..."