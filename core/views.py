from django.shortcuts import render

# Create your views here.
import requests
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from .forms import QuestionForm, RegisterForm, LoginForm
from .models import Conversation
from django.contrib.auth.models import User
import os
from dotenv import load_dotenv



def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password1 = form.cleaned_data['password1']
            password2 = form.cleaned_data['password2']

            if password1 != password2:
                messages.error(request, 'Las contraseñas no coinciden.')
                return redirect('register')

            if User.objects.filter(username=username).exists():
                messages.error(request, 'El nombre de usuario ya existe.')
                return redirect('register')

            user = User.objects.create_user(username=username, password=password1)
            login(request, user)
            return redirect('/')
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
                return redirect('/')
            else:
                messages.error(request, 'Usuario o contraseña incorrectos.')
                return redirect('login')
    else:
        form = LoginForm()

    return render(request, 'core/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('login')

def index(request):
    load_dotenv()  # Carga las variables del .env
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

    if request.method == 'POST':
        form = QuestionForm(request.POST)
        if form.is_valid():
            topic = form.cleaned_data['topic']
            question = form.cleaned_data['question']

            try:
                response = requests.post(
                    url="https://openrouter.ai/api/v1/chat/completions", 
                    headers={
                        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "mistralai/mistral-7b-instruct:free",
                        "messages": [{"role": "user", "content": question}]
                    }
                ).json()

                ai_response = response.get('choices', [{}])[0].get('message', {}).get('content', 'No hubo respuesta.')

                Conversation.objects.create(
                    user=request.user,
                    topic=topic,
                    question=question,
                    response=ai_response
                )
            except Exception as e:
                messages.error(request, f"Error al comunicarse con la IA: {e}")

            return redirect('/')

    else:
        form = QuestionForm()

    conversations = Conversation.objects.filter(user=request.user).order_by('-created_at')[:10]
    return render(request, 'core/index.html', {
        'form': form,
        'conversations': conversations
    })