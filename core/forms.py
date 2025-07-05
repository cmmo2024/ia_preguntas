from django import forms
from .models import Subject, Topic

IA_MODELS = (
    ('qwen/qwen-2.5-72b-instruct:free', 'Qwen 2.5'),
    ('mistralai/mistral-7b-instruct:free', 'Mistral 7B'),
)

class QuestionForm(forms.Form):
    subject = forms.ModelChoiceField(
        queryset=Subject.objects.all(), 
        label="Asignatura", 
        empty_label="Selecciona una asignatura",
        widget=forms.Select(attrs={'class': 'form-select truncate'}))
    topic = forms.ModelChoiceField(
        queryset=Topic.objects.none(), 
        label="Tema", 
        empty_label="Selecciona un Tema",
        widget=forms.Select(attrs={'class': 'form-select truncate'}))
    question = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 3,
            'class': 'form-control',
            'placeholder': 'Escribe aquí tu pregunta...',
            'style': 'width: 100%; resize: none;'}),
        label="Tu pregunta",
        required=False  # 👈 Ahora no es obligatorio
    )
    model = forms.ChoiceField(choices=IA_MODELS, label="Modelo de IA")

class RegisterForm(forms.Form):
    username = forms.CharField(label="Usuario", max_length=100)
    password1 = forms.CharField(label="Contraseña", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Repetir contraseña", widget=forms.PasswordInput)

class LoginForm(forms.Form):
    username = forms.CharField(label="Usuario")
    password = forms.CharField(label="Contraseña", widget=forms.PasswordInput)

class UploadTopicsForm(forms.Form):
    file = forms.FileField(label="Archivo .txt con temas", help_text="El nombre del archivo será el nombre de la asignatura. Formato: nombre_tema: descripción_tema")