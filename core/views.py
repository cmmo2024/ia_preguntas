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
    # Opcional: Limpiar mensajes antes de cerrar sesión
    storage = messages.get_messages(request)
    for message in storage:
        pass  # Esto "consume" los mensajes sin mostrar
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
    load_dotenv()

    # Cargar valores de filtro desde URL (?subject=X&topic=Y)
    subject_filter = request.GET.get('subject')
    topic_filter = request.GET.get('topic')

    # Cargamos todas las conversaciones del usuario
    conversations = Conversation.objects.filter(user=request.user)

    # Aplicamos filtros si existen
    if subject_filter:
        conversations = conversations.filter(topic__subject_id=subject_filter)
    
    if topic_filter:
        conversations = conversations.filter(topic_id=topic_filter)

    # Limitamos a últimas 10 conversaciones
    conversations = conversations.order_by('-created_at')[:10]

    if request.method == 'POST':
        form_data = request.POST.copy()
        form = QuestionForm(form_data)

        # Actualizar queryset de topic
        if 'subject' in request.POST:
            try:
                subject_id = int(request.POST.get('subject'))
                form.fields['topic'].queryset = Topic.objects.filter(subject_id=subject_id)
            except (ValueError, TypeError):
                form.fields['topic'].queryset = Topic.objects.none()

        if form.is_valid():
            selected_subject = form.cleaned_data['subject']
            selected_topic = form.cleaned_data['topic']
            question = form.cleaned_data['question']
            selected_model = form.cleaned_data['model']

            # Guardar en sesión para mantener selección
            request.session['subject_id'] = selected_subject.id
            request.session['topic_id'] = selected_topic.id
            request.session['model'] = selected_model

            # 👇 Si se hizo clic en "Examen", generar preguntas tipo test
            if 'generate_exam' in request.POST:
                try:
                    prompt = f"""
                    Eres un profesor virtual. Genera 7 preguntas de opción múltiple sobre '{selected_topic.name}' 
                    de la asignatura '{selected_subject}'.
                    Contexto: {selected_topic.description or ''}
                    
                    Cada pregunta debe tener 4 opciones (a, b, c, d) y señalar cuál es la correcta.
                    
                    Ejemplo:
                    
                    PREGUNTA 1: ¿Cuánto es 2 + 2?
                    a) 3
                    b) 5
                    c) 4
                    d) 0
                    Correcta: c
                    
                    ... (repetir para 7 preguntas)
                    """

                    response = requests.post(
                        url="https://openrouter.ai/api/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": selected_model,
                            "messages": [{"role": "user", "content": prompt}],
                            "max_tokens": 1000,
                            "temperature": 0.6
                        }
                    )

                    if response.status_code != 200:
                        raise Exception(f"Error de API: {response.status_code} - {response.text}")

                    ai_response = response.json().get('choices', [{}])[0].get('message', {}).get('content', '')
                    
                    questions = parse_exam(ai_response)
                    request.session['exam_questions'] = questions
                    request.session['exam_subject'] = str(selected_subject)
                    request.session['exam_topic'] = str(selected_topic.name)

                    return redirect('exam')

                except Exception as e:
                    messages.error(request, f"⚠️ Error al generar el examen: {e}")
                    return redirect('index')

            elif 'submit_question' in request.POST:
                if not question.strip():
                    messages.error(request, "⚠️ El campo 'Pregunta' es obligatorio.")
                    return render(request, 'core/index.html', {
                        'form': form,
                        'conversations': conversations,
                        'subjects': Subject.objects.all(),
                        'topics': Topic.objects.all(),
                        'subject_filter': subject_filter,
                        'topic_filter': topic_filter
                    })

                try:
                    # Añadimos contexto de la asignatura y tema
                    descripcion = selected_topic.description or ""
                    tema = selected_topic.name or ""
                    full_prompt = f"""Contexto: Asignatura-{selected_subject.name}, Tema-{tema},
                                 Descripcion-{descripcion} Pregunta: {question} (Responde en menos de 300 tokens
                                   y a preguntas que no se ajuste al Contexto responder No aplica al Tema)"""

                    response = requests.post(
                        url="https://openrouter.ai/api/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": selected_model,
                            "messages": [{"role": "user", "content": full_prompt}],
                            "temperature": 0.7,
                            "top_p": 0.9,
                        }
                    )

                    if response.status_code != 200:
                        raise Exception(f"Error de API: {response.status_code} - {response.text}")

                    ai_response = response.json().get('choices', [{}])[0].get('message', {}).get('content', 'Sin respuesta.')

                    Conversation.objects.create(
                        user=request.user,
                        topic=selected_topic,
                        question=question,
                        response=ai_response
                    )

                except Exception as e:
                    messages.error(request, f"⚠️ Error al comunicarse con la IA: {e}")
                    return redirect('index')

        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"⚠️ Error en '{form.fields[field].label}': {error}")

            return render(request, 'core/index.html', {
                'form': form,
                'conversations': conversations,
                'subjects': Subject.objects.all(),
                'topics': Topic.objects.all(),
                'subject_filter': subject_filter,
                'topic_filter': topic_filter
            })

    else:
        # Carga inicial con datos guardados o vacíos
        initial_data = {
            'subject': request.session.get('subject_id'),
            'topic': request.session.get('topic_id'),
            'model': request.session.get('model')
        }
        form = QuestionForm(initial=initial_data)

    # Pasamos todas las asignaturas y temas para los filtros
    subjects = Subject.objects.all()
    topics = Topic.objects.all()

    # 👇 Si hay un subject_filter, mostramos solo sus temas
    if subject_filter:
        try:
            topics = topics.filter(subject_id=int(subject_filter))
        except ValueError:
            topics = Topic.objects.none()  # O vacío si el subject_id no es válido


    return render(request, 'core/index.html', {
        'form': form,
        'conversations': conversations,
        'subjects': subjects,
        'topics': topics,
        'subject_filter': subject_filter,
        'topic_filter': topic_filter
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
    if not conversation:
        # Opcional: manejar caso donde no existe la conversación
        messages.error(request, "⚠️ No se encontró esa conversación.")
        return redirect('index')
    conversation.delete()
     # Solo añadimos el mensaje si el usuario sigue autenticado
    if request.user.is_authenticated:
        messages.success(request, "✅ Conversación eliminada correctamente.")
    return redirect('index')

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.http import HttpResponse

@login_required
def exam_view(request):
    questions = request.session.get('exam_questions', [])
    topic_name = request.session.get('exam_topic', 'Tema')
    subject_name = request.session.get('exam_subject', 'Asignatura')

    if not questions:
        messages.error(request, "⚠️ No hay preguntas disponibles.")
        return redirect('index')

    # 👇 Obtenemos la asignatura y el tema desde la primera pregunta
    #first_question = questions[0] if questions else None
    #topic_name = first_question['topic'].name if 'topic' in first_question else "Tema"
    #subject_name = first_question['subject'].name if 'subject' in first_question else "Asignatura"

    return render(request, 'core/exam.html', {
        'questions': questions,
        'topic_name': topic_name,
        'subject_name': subject_name
    })


import re

def parse_exam(text):
    if not isinstance(text, str):
        raise ValueError("parse_exam() requiere un texto (str), no una lista u otro tipo")
    text = re.sub(r'\r', '', text)
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    questions = []
    current_question = None

    for line in lines:
        q_match = re.match(r"PREGUNTA\s+(\d+):(.+)", line)
        opt_match = re.match(r"([a-d])\)\s*(.+)", line)
        correct_match = re.search(r"Correcta:\s*([a-d])", line)

        if q_match:
            if current_question:
                questions.append(current_question)

            current_question = {
                'number': q_match.group(1),
                'text': q_match.group(2).strip(),
                'options': [],
                'correct': ''
            }

        elif current_question and opt_match:
            letter, option_text = opt_match.groups()
            current_question['options'].append(option_text.strip())

        elif current_question and correct_match:
            current_question['correct'] = correct_match.group(1)

    if current_question and len(current_question['options']) == 4:
        questions.append(current_question)

    return questions


@login_required
def submit_exam(request):
    if request.method == 'POST':
        questions = request.session.get('exam_questions', [])
        #print("Type of questions:", type(questions))  # 👉 Debe mostrar <class 'list'>
        #print("Questions:", questions)  # 👉 Debe mostrar la lista de preguntas
        if not isinstance(questions, list):
            messages.error(request, "⚠️ Datos del examen inválidos.")
            return redirect('index')

        user_answers = {}
        correct_count = 0

        for key in request.POST:
            if key.startswith('q'):
                suffix = key[1:]

                # Verificar que sea dígito antes de convertir
                if not suffix.isdigit():
                    continue  # o mostrar mensaje de error

                question_num = int(suffix) - 1

                # Asegurarnos que el índice esté dentro del rango
                if question_num < 0 or question_num >= len(questions):
                    messages.warning(request, f"Pregunta {question_num + 1} fuera de rango.")
                    continue

                user_answer_index = request.POST.get(key)

                if user_answer_index.isdigit():
                    selected_index = int(user_answer_index)
                    correct_letter = chr(97 + selected_index)
                else:
                    messages.warning(request, f"Selección inválida en pregunta {question_num + 1}")
                    continue

                # 👇 Aquí está la línea que fallaba:
                correct_answer = questions[question_num]['correct']

                is_correct = correct_letter == correct_answer
                if is_correct:
                    correct_count += 1

                user_answers[key] = {
                    'text': questions[question_num]['text'],
                    'options': questions[question_num]['options'],
                    'selected': correct_letter,
                    'correct': correct_answer,
                    'is_correct': is_correct
                }

        return render(request, 'core/exam_result.html', {
            'user_answers': user_answers,
            'total': len(questions),
            'correct_count': correct_count
        })

    else:
        return redirect('index')