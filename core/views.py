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
            try:
                # 👇 Añadimos la descripción del tema al prompt
                context = selected_topic_id.description or ""
                full_prompt = f"Contexto: {context}\n\nPregunta: {question}"

                response = requests.post(
                    url="https://openrouter.ai/api/v1/chat/completions", 
                    headers={
                        "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": selected_model,
                        "messages": [{"role": "user", "content": full_prompt}],
                        # 👇 Limitamos los tokens de salida
                        "max_tokens": 200,  # Cambia este número si necesitas más o menos tokens
                        "temperature": 0.7,  # Más bajo = más preciso | Más alto = más creativo
                        "top_p": 0.9,
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


from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied
from django.core.files.uploadedfile import UploadedFile

from .forms import UploadTopicsForm
from .models import Subject, Topic
import chardet

def is_superuser(user):
    return user.is_superuser

@user_passes_test(is_superuser, login_url='index')
def upload_topics_view(request):
    if request.method == 'POST':
        form = UploadTopicsForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = request.FILES['file']

            # 👇 Nombre del archivo sin extensión → nombre de la asignatura
            subject_name = os.path.splitext(uploaded_file.name)[0].replace('_', ' ').title()

            # 👇 Crear o obtener asignatura
            subject, created = Subject.objects.get_or_create(name=subject_name)

            if not created:
                messages.warning(request, f"⚠️ La asignatura '{subject_name}' ya existía.")
            else:
                messages.success(request, f"✅ Asignatura '{subject_name}' creada.")

            try:
                raw_data = uploaded_file.read()
                result = chardet.detect(raw_data)
                encoding = result['encoding'] or 'utf-8'
                decoded_file = raw_data.decode(encoding)

                lines = decoded_file.split('\n')

                count = 0
                for line in lines:
                    if ':' in line:
                        name, description = line.strip().split(':', 1)
                        Topic.objects.update_or_create(
                            subject=subject,
                            name=name.strip(),
                            defaults={'description': description.strip()}
                        )
                        count += 1

                messages.success(request, f"📚 Se cargaron {count} temas para '{subject_name}'.")
            except UnicodeDecodeError as e:
                messages.error(request, f"❌ Error al decodificar el archivo: {e}")
            except Exception as e:
                messages.error(request, f"⚠️ Error al procesar el archivo: {e}")

        else:
            messages.error(request, "⚠️ Formulario inválido.")

    else:
        form = UploadTopicsForm()

    return render(request, 'core/upload_topics.html', {'form': form})


from .models import Conversation
from django.shortcuts import get_object_or_404

@login_required
def delete_conversation(request, conv_id):
    conversation = get_object_or_404(Conversation, id=conv_id, user=request.user)
    conversation.delete()
    messages.success(request, "✅ Conversación eliminada correctamente.")
    return redirect('index')