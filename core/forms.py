from django import forms
from .models import Subject, Topic

IA_MODELS = (
    ('mistralai/mistral-7b-instruct:free', 'Mistral 7B'),
    ('qwen/qwen-2.5-72b-instruct:free', 'Qwen 2.5'),
)

class QuestionForm(forms.Form):
    subject = forms.ModelChoiceField(queryset=Subject.objects.all(), label="Asignatura")
    topic = forms.ModelChoiceField(queryset=Topic.objects.none(), label="Tema")  # Se ajustará dinámicamente
    question = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), label="Tu pregunta")
    model = forms.ChoiceField(choices=IA_MODELS, label="Modelo de IA")

class RegisterForm(forms.Form):
    username = forms.CharField(label="Usuario", max_length=100)
    password1 = forms.CharField(label="Contraseña", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Repetir contraseña", widget=forms.PasswordInput)

class LoginForm(forms.Form):
    username = forms.CharField(label="Usuario")
    password = forms.CharField(label="Contraseña", widget=forms.PasswordInput)

class UploadTopicsForm(forms.Form):
    subject = forms.ModelChoiceField(queryset=Subject.objects.all(), label="Selecciona la asignatura")
    file = forms.FileField(label="Archivo .txt con temas", help_text="Formato: nombre_tema: descripción_tema")