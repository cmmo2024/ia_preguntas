from django import forms
from .models import TOPICS

class QuestionForm(forms.Form):
    topic = forms.ChoiceField(choices=TOPICS, label="Tema")
    question = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), label="Tu pregunta")

class RegisterForm(forms.Form):
    username = forms.CharField(label="Usuario", max_length=100)
    password1 = forms.CharField(label="Contraseña", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Repetir contraseña", widget=forms.PasswordInput)

class LoginForm(forms.Form):
    username = forms.CharField(label="Usuario")
    password = forms.CharField(label="Contraseña", widget=forms.PasswordInput)