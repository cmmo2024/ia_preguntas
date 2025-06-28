import os
import requests
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .forms import QuestionForm, RegisterForm, LoginForm
from .models import Conversation, Topic
from dotenv import load_dotenv
from django.contrib.auth.models import User  # 👈 Añade esta línea

def logout_view(request):
    logout(request)
    return redirect('login')

def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password1']

            if User.objects.filter(username=username).exists():
                messages.error(request, "El nombre de usuario ya está en uso.")
                return render(request, 'core/register.html', {'form': form})

            user = User.objects.create_user(username=username, password=password)
            login(request, user)
            return redirect('index')
    else:
        form = RegisterForm()

    return render(request, 'core/register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)

            if user is not None:
                login(request, user)
                return redirect('index')
            else:
                messages.error(request, "Usuario o contraseña incorrectos.")
    else:
        form = LoginForm()

    return render(request, 'core/login.html', {'form': form})

@login_required
def index(request):
    load_dotenv()  # Carga las variables del .env
    #print(os.getenv("OPENROUTER_API_KEY"))  # Para probarla desde consola
    if request.method == 'POST':
        form = QuestionForm(request.POST)
        # Actualizar queryset de topic
        if 'subject' in request.POST:
            try:
                subject_id = int(request.POST.get('subject'))
                form.fields['topic'].queryset = Topic.objects.filter(subject_id=subject_id)
            except (ValueError, TypeError):
                form.fields['topic'].queryset = Topic.objects.none()
        if form.is_valid():
            selected_subject = form.cleaned_data['subject']
            selected_topic_id = form.cleaned_data['topic']
            question = form.cleaned_data['question']
            selected_model = form.cleaned_data['model']
           # print("Modelo seleccionado:", selected_model)  # 👈 Verifica qué valor llega
            try:
                response = requests.post(
                    url="https://openrouter.ai/api/v1/chat/completions", 
                    headers={
                        "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": selected_model,
                        "messages": [{"role": "user", "content": question}]
                    }
                )

                if response.status_code != 200:
                    raise Exception(f"Error de API: {response.status_code} - {response.text}")

                ai_response = response.json().get('choices', [{}])[0].get('message', {}).get('content', 'Sin respuesta.')
                

                Conversation.objects.create(
                    user=request.user,
                    topic=selected_topic_id,
                    question=question,
                    response=ai_response
                )

            except Exception as e:
                messages.error(request, f"⚠️ Error al comunicarse con la IA: {e}")
                return redirect('index')
        else:
            # 👇 Muestra los errores del formulario
            print("Errores del formulario:", form.errors)

            # 👇 También puedes mostrar un mensaje al usuario
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Error en '{form.fields[field].label}': {error}")
    else:
        form = QuestionForm(initial={'model': 'mistralai/mistral-7b-instruct:free'})

    conversations = Conversation.objects.filter(user=request.user).order_by('-created_at')[:10]
    return render(request, 'core/index.html', {
        'form': form,
        'conversations': conversations
    })

def load_topics(request):
    subject_id = request.GET.get('subject')
    topics = Topic.objects.filter(subject_id=subject_id).values('id', 'name')
    return JsonResponse({'topics': list(topics)})

def about_view(request):
    return render(request, 'core/about.html')

def help_view(request):
    return render(request, 'core/help.html')