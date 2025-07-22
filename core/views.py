import os
import requests
from django.shortcuts import render, redirect
from django.db.models import Q, Count
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.template.loader import render_to_string 
from .forms import QuestionForm, RegisterForm, LoginForm
from .models import Conversation, Topic
from dotenv import load_dotenv
from django.contrib.auth.models import User  # 👈 Añade esta línea

load_dotenv() #Carga variables de entorno

def logout_view(request):
    # Opcional: Limpiar mensajes antes de cerrar sesión
    storage = messages.get_messages(request)
    for message in storage:
        pass  # Esto "consume" los mensajes sin mostrar
    logout(request)
    return redirect('login')

from django.contrib.auth import login, authenticate
from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import RegisterForm
from .models import UserProfile
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

# views.py
def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password1']

            # Verificar si el usuario ya existe
            if User.objects.filter(username=username).exists():
                messages.error(request, "El nombre de usuario ya está en uso.")
                return render(request, 'core/register.html', {'form': form})
            
            # Crear usuario
            user = User.objects.create_user(
                username=username,
                password=password
            )
            # 👇 Autenticamos al usuario para que tenga backend asignado
            user = authenticate(username=username, password=password)

            if user is not None:
                  login(request, user)
                  return redirect('index')
            else:
                 messages.error(request, "No se pudo iniciar sesión automáticamente.")
                 return render(request, 'core/register.html', {'form': form})    
        else:
            # Mostrar todos los errores del formulario
            for field, errors in form.errors.items():
                for error in errors:
                    if field == '__all__':
                        messages.error(request, f"{error}")
                    else:
                        messages.error(request, f"{form.fields[field].label}: {error}")
            return render(request, 'core/register.html', {'form': form})
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

# Index----Vista de Tutor-IA-------------------------------------------------
@login_required
def index(request):
    
    profile = request.user.userprofile
    profile.reset_period_if_needed()
    
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
        #-----Chequeo del Plan--------
        if not profile.can_make_request():
            messages.warning(request, "Has alcanzado el límite de peticiones.")
            return redirect('profile')
        #-----Chequeo del Plan--------


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
            
            # Validar acceso al tema según plan
            if request.user.is_authenticated and request.user.userprofile.plan == 'free':
                first_topic = selected_subject.first_topic()
                if first_topic and selected_topic.id != first_topic.id:
                    messages.warning(
                        request, 
                        f"Tu plan Gratuito solo puedes hacer preguntas al primer tema de cada asignatura: '{first_topic.name}'"
                    )
                    return redirect('profile')

            # Guardar en sesión para mantener selección
            request.session['subject_id'] = selected_subject.id
            request.session['topic_id'] = selected_topic.id
            request.session['model'] = selected_model

            # 👇 Si se hizo clic en "Examen", generar preguntas tipo test
            if 'generate_exam' in request.POST:
                try:
                    prompt = f"""
                    Eres un profesor virtual. Genera 15 preguntas de opción múltiple sobre '{selected_topic.name}' 
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
                    Importante: No hagas comentarios, solo responde con el formato del ejemplo dado
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
                    
                    profile.increment_request() # Incrementar numero de request para plan
                    ai_response = response.json().get('choices', [{}])[0].get('message', {}).get('content', '')
                    
                    questions = parse_exam(ai_response)
                    request.session['exam_questions'] = questions
                    request.session['exam_subject'] = str(selected_subject)
                    request.session['exam_topic'] = str(selected_topic.name)

                    return redirect('exam')

                except Exception as e:
                    messages.error(request, f"Error al generar el examen: {e}")
                    return redirect('index')

            elif 'submit_question' in request.POST:
                if not question.strip():
                    messages.error(request, "El campo 'Pregunta' es obligatorio.")
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
                    profile.increment_request() # Incrementar numero de request para plan

                except Exception as e:
                    messages.error(request, f"Error al comunicarse con la IA: {e}")
                    return redirect('index')

        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Error en '{form.fields[field].label}': {error}")

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

    # Si hay un subject_filter, cargamos solo sus temas
    if subject_filter and subject_filter.isdigit():
        topics = Topic.objects.filter(subject_id=int(subject_filter))
    else:
        topics = Topic.objects.all()

    subjects = Subject.objects.all()

    if request.method == 'GET':
    # Si es una solicitud AJAX, devolvemos solo el historial filtrado
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            html = render_to_string('core/_conversations.html', {
                'conversations': conversations,
            }, request=request)
            return JsonResponse({'html': html})


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
    support_email = getattr(settings, 'SUPPORT_EMAIL', 'soporte@tutoria.com')
    return render(request, 'core/about.html', {'support_email': support_email})

def help_view(request):
    support_email = getattr(settings, 'SUPPORT_EMAIL', 'soporte@tutoria.com')
    return render(request, 'core/help.html', {'support_email': support_email})


from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied
from django.core.files.uploadedfile import UploadedFile

from .forms import UploadTopicsForm
from .models import Subject, Topic
import chardet

def is_superuser(user):
    return user.is_superuser

# Vista de Cargar Temas de archivo----------------------------------------------------------------------
# views.py
@user_passes_test(lambda u: u.is_authenticated, login_url='login')
def upload_topics_view(request):
    # Verificar plan o permisos
    profile = request.user.userprofile
    if not (profile.plan == 'premium' or request.user.is_superuser):
        messages.error(request, "⚠️ Esta funcionalidad requiere plan Premium o ser administrador.")
        return redirect('index')

    if request.method == 'POST':
        form = UploadTopicsForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = request.FILES['file']
            subject_name = os.path.splitext(uploaded_file.name)[0].replace('_', ' ').title()

            # Decidir si es pública o privada
            is_public = request.user.is_superuser and 'make_public' in request.POST

            # Crear o obtener asignatura
            # Decidir si es pública o privada
            if request.user.is_superuser and 'make_public' in request.POST:
                # Crear como pública
                subject, created = Subject.objects.get_or_create(
                    name=subject_name,
                    is_public=True,
                    defaults={'user': None}
                )
            else:
                # Crear como privada del usuario
                subject, created = Subject.objects.get_or_create(
                    name=subject_name,
                    user=request.user,
                    is_public=False
                )

            try:
                raw_data = uploaded_file.read()
                result = chardet.detect(raw_data)
                encoding = result['encoding'] or 'utf-8'
                decoded_file = raw_data.decode(encoding)
                lines = decoded_file.split('\n')

                count = 0
                for line in lines:
                    if ':' in line:
                        name, desc = line.strip().split(':', 1)
                        Topic.objects.update_or_create(
                            subject=subject,
                            name=name.strip(),
                            defaults={'description': desc.strip()}
                        )
                        count += 1

                tipo = "pública" if is_public else "privada"
                messages.success(request, f"📚 Se cargaron {count} temas en '{subject_name}' ({tipo}).")

            except Exception as e:
                messages.error(request, f"Error: {e}")

    else:
        form = UploadTopicsForm()

    # Mostrar asignaturas: públicas + del usuario
    subjects = Subject.objects.filter(
        Q(is_public=True) | Q(user=request.user)
    ).annotate(topic_count=Count('topic'))

    return render(request, 'core/upload_topics.html', {
        'form': form,
        'subjects': subjects,
        'is_superuser': request.user.is_superuser
    })

# Borrar Asignatura----------------------------------------------------------------------
@login_required
def delete_subject(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id)

    # Solo puede borrar:
    # - Si es suya (privada)
    # - O si es pública y es superusuario
    if subject.user == request.user or (subject.is_public and request.user.is_superuser):
        subject.delete()
        messages.success(request, f"Asignatura '{subject.name}' eliminada.")
    else:
        messages.error(request, "No tienes permiso para eliminar esta asignatura.")

    return redirect('upload_topics')

# Borrar Conversación----------------------------------------------------------------------
from .models import Conversation
from django.shortcuts import get_object_or_404

@login_required
def delete_conversation(request, conv_id):
    conversation = get_object_or_404(Conversation, id=conv_id, user=request.user)
    if not conversation:
        # Opcional: manejar caso donde no existe la conversación
        messages.error(request, "No se encontró esa conversación.")
        return redirect('index')
    conversation.delete()
     # Solo añadimos el mensaje si el usuario sigue autenticado
    if request.user.is_authenticated:
        messages.success(request, "Conversación eliminada correctamente.")
    return redirect('index')

# Vista de Examen----------------------------------------------------------------------
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.http import HttpResponse

@login_required
def exam_view(request):
   
    questions = request.session.get('exam_questions', [])
    topic_name = request.session.get('exam_topic', 'Tema')
    subject_name = request.session.get('exam_subject', 'Asignatura')

    if not questions:
        messages.error(request, "No hay preguntas disponibles.")
        return redirect('index')

    return render(request, 'core/exam.html', {
        'questions': questions,
        'topic_name': topic_name,
        'subject_name': subject_name
    })

# Parser de Examen----------------------------------------------------------------------
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

# Aplicar Examen----------------------------------------------------------------------

from .models import Exam

@login_required
def submit_exam(request):
    if request.method == 'POST':
        questions = request.session.get('exam_questions', [])
        topic_name = request.session.get('exam_topic', 'Tema')
        subject_name = request.session.get('exam_subject', 'Asignatura')

        if not isinstance(questions, list):
            messages.error(request, "Datos del examen inválidos.")
            return redirect('index')

        user_answers = {}
        correct_count = 0

        for key in request.POST:
            if key.startswith('q'):
                suffix = key[1:]
                if not suffix.isdigit():
                    continue
                question_num = int(suffix) - 1
                if question_num < 0 or question_num >= len(questions):
                    continue

                user_answer_index = request.POST.get(key)
                selected_letter = chr(97 + int(user_answer_index))
                correct_letter = questions[question_num]['correct']
                is_correct = selected_letter == correct_letter

                if is_correct:
                    correct_count += 1

                user_answers[key] = {
                    'text': questions[question_num]['text'],
                    'options': questions[question_num]['options'],
                    'selected': selected_letter,
                    'correct': correct_letter,
                    'is_correct': is_correct
                }

        # Guardar en la base de datos
        try:
            exam = Exam.objects.create(
                user=request.user,
                subject_name=subject_name,
                topic_name=topic_name,
                questions=questions,
                user_answers=user_answers,
                correct_count=correct_count,
                total_questions=len(questions)
            )
        except Exception as e:
            messages.error(request, f"Error al guardar el examen: {e}")

        return render(request, 'core/exam_result.html', {
            'user_answers': user_answers,
            'total': len(questions),
            'correct_count': correct_count
        })
    else:
        return redirect('index')
    
# Perfil de usuario----------------------------------------------------------------------
from .models import UserProfile, Conversation
from django.shortcuts import render
from .models import UserProfile, Exam

@login_required
def profile_view(request):
    # Obtener perfil del usuario
    profile = request.user.userprofile
    profile.reset_period_if_needed()  # Reinicia cuota diaria si es nuevo día

    # Obtener últimos exámenes (opcional)
    exams = Exam.objects.filter(user=request.user).order_by('-created_at')[:10]

    # Calcular estadísticas (solo si las muestras en la plantilla)
    total_exams = exams.count()
    correct_answers = sum(exam.correct_count for exam in exams)
    total_questions = sum(exam.total_questions for exam in exams)
    average_score = round(correct_answers / total_questions * 100, 2) if total_questions else 0

    context = {
        'profile': profile,
        'exams': exams,
        'total_exams': total_exams,
        'correct_answers': correct_answers,
        'total_questions': total_questions,
        'average_score': average_score,
    }

    return render(request, 'core/profile.html', context)

# Borrar examen de historial y de la BD---------------------------
from django.shortcuts import get_object_or_404, redirect

@login_required
def delete_exam(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id, user=request.user)
    exam.delete()
    messages.success(request, "Examen eliminado correctamente.")
    return redirect('profile')

# exam_detail------------------------------------------------------------------
@login_required
def exam_detail(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id, user=request.user)
    return render(request, 'core/exam_detail.html', {'exam': exam})

# Pago con Stripe...--------------------------------------------------------------------
import stripe
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, reverse
from django.urls import reverse
from django.contrib import messages
from django.http import JsonResponse
import json
from datetime import timezone

@login_required
def create_payment(request):
    profile = request.user.userprofile
    if profile.plan == 'premium':
        messages.warning(request, "Ya tienes el plan Premium.")
        return redirect('profile')

    stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
    
    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "unit_amount": 999,  # $9.99 USD
                        "product_data": {
                            "name": "Plan Premium - Tutor con IA",
                            "description": "Acceso completo por 30 días"
                        },
                    },
                    "quantity": 1,
                }
            ],
            mode="subscription",  # o "payment" si es pago único
            success_url=request.build_absolute_uri(reverse('payment_success')),
            cancel_url=request.build_absolute_uri(reverse('payment_cancelled')),
        )
        return redirect(checkout_session.url, code=303)
    except Exception as e:
        messages.error(request, f"Error al procesar el pago: {str(e)}")
        return redirect('profile')
    
    # Pago exitoso--------------------------------------------------------------------
@login_required
def payment_success(request):
    profile = request.user.userprofile
    profile.plan = 'premium'
    profile.period_start = timezone.now().date()
    profile.daily_ia_requests = 0
    profile.daily_exams = 0
    profile.save()

    messages.success(request, "🎉 ¡Gracias por tu pago! Ahora tienes acceso completo.")
    return redirect('profile')

# Pago cancelado------------------------------------------------------------------------
def payment_cancelled(request):
    messages.info(request, "El pago fue cancelado.")
    return redirect('profile')
# Pago Transfermovil-------------------------------------------------------------------
# views.py
import re
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import UserProfile
from django.utils import timezone

@login_required
def transfermovil_view(request):
    account_number = "9238959870690379"
    amount_required = "500.00 CUP"

    if request.method == 'POST':
        sms_text = request.POST.get('sms_text', '').strip()

        # Patrón para validar el texto del SMS
        pattern = r"Beneficiario:\s*(\d{4}[\dX]{8,}\d{4})[\s\S]*?Monto:\s*([\d\.]+)\s*CUP[\s\S]*?Nro.\s*Transaccion:\s*\w+"
        match = re.search(pattern, sms_text)

        if not match:
            messages.error(request, "El texto del SMS no tiene el formato correcto.")
        else:
            beneficiary = match.group(1)
            amount = match.group(2)

            # Validar que coincidan 4 primeros y últimos dígitos
            if beneficiary.startswith(account_number[:4]) and beneficiary.endswith(account_number[-4:]):
                # Validar monto
                if float(amount) == 500.0:
                    profile = request.user.userprofile
                    profile.plan = 'premium'
                    profile.period_start = timezone.now().date()
                    profile.daily_ia_requests = 0
                    profile.daily_exams = 0
                    profile.save()
                    messages.success(request, "🎉 ¡Pago validado! Tu plan ha sido actualizado a Premium.")
                    return redirect('profile')
                else:
                    messages.error(request, f"El monto del SMS debe ser {amount_required}.")
            else:
                messages.error(request, "Los dígitos del beneficiario no coinciden con la cuenta destino.")

    context = {
        'account_number': account_number,
        'amount_required': amount_required
    }
    return render(request, 'core/transfermovil.html', context)
   

# Chatbot sin IA ---------------------------------------------------
from django.http import JsonResponse
import json
import unicodedata

def faq_chatbot(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            question = data.get('question', '').strip().lower()
            
            # Función para quitar acentos y normalizar texto
            def normalize(text):
                return ''.join(
                    c for c in unicodedata.normalize('NFD', text)
                    if unicodedata.category(c) != 'Mn'
                ).lower().replace("?", "").strip()

            normalized_question = normalize(question)

            # Respuestas predefinidas (sin IA)
            responses = {
                "como funciona el examen": "El examen te permite generar un cuestionario tipo test con 7 preguntas basadas en un tema específico.",
                "puedo usar la app sin registrarme": "Sí, puedes hacer hasta 5 preguntas como invitado, pero no podrás guardar historial ni generar exámenes.",
                "como hago una pregunta a la ia": "Selecciona una asignatura y tema, escribe tu pregunta y haz clic en 'Enviar Pregunta'.",
                "que modelos de ia usan": "Usamos Mistral 7B y Qwen 2.5, ambos gratuitos y eficientes.",
                "cuantas preguntas puedo hacer por dia": "Usuarios gratuitos pueden hacer 5 preguntas diarias. Usuarios premium: 100 preguntas.",
                "como genero un examen": "Haz clic en el botón 'Aplicar Examen' tras seleccionar una asignatura y tema.",
                "donde veo mi historial": "Tu historial aparece automáticamente después de enviar preguntas.",
                "por que no me deja hacer mas preguntas": "Puede ser que hayas alcanzado tu límite diario.",
                "como mejoro a premium": "Ve a tu perfil y haz clic en 'Upgrade a Premium'",
                "que pasa si pago el plan": "Podrás hacer hasta 100 preguntas diarias y acceder a todos los temas y exámenes.",
                "como elimino mi historial": "Haz clic en el botón 'Eliminar' junto a cada conversación.",
                "el login social esta disponible": "Actualmente está pendiente. Pronto ofreceremos inicio de sesión con Google y Facebook.",
                "tienen soporte tecnico": "Sí, escríbenos al correo de soporte desde la página de ayuda.",
                "como contacto con soporte": "En la sección de Ayuda encontrarás un correo de contacto.",
                "hay limite de tiempo en el examen": "No, tienes todo el tiempo que necesites para responderlo.",
                "se guardan mis respuestas del examen": "Sí, se muestran al final del examen.",
                "cual es el limite de uso gratis": "Usuarios gratuitos pueden hacer 5 preguntas diarias y solo tienen acceso al primer tema de cada asignatura.",
                "como se reinician las cuotas": "Cada 30 días, según tu fecha de registro.",
                "que pasa al terminar el periodo": "Vuelves al plan gratuito, con 5 preguntas diarias y temas limitados.",
                "como subo nuevos temas": "Solo usuarios administradores pueden cargar temas desde el panel de carga de archivos.",
                "donde estan mis estadisticas": "Todas tus estadísticas están en la página de tu Perfil.",
                "como corrijo una respuesta erronea de la ia": "Lo sentimos, actualmente no puedes corregir directamente las respuestas de la IA.",
                "puedo usar la app offline": "No, necesitas conexión a internet para interactuar con la IA."
            }

            answer = "Lo siento, no tengo una respuesta para esa pregunta aún. Contáctanos por correo."

            for key in responses:
                if normalized_question in normalize(key):
                    answer = responses[key]
                    break

            return JsonResponse({'answer': answer})
        except json.JSONDecodeError:
            return JsonResponse({'answer': '⚠️ Error al procesar tu pregunta.'})
    else:
        return JsonResponse({'answer': '⚠️ Solo acepto preguntas POST.'})
    
# Editar Perfil de Usuariofrom django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash  # Importante tras cambiar contraseña
from django.http import HttpResponse
from .forms import EditProfileForm
from .models import ProfessionalCategory


@login_required
def edit_profile_view(request):
    if request.method == 'POST':
        user = request.user
        user.username = request.POST.get('username', user.username)
        user.email = request.POST.get('email', user.email)
        user.first_name = request.POST.get('first_name', user.first_name)

        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')

        # Guardar categoría profesional
        category = request.POST.get('category', '')
        profile = user.userprofile
        if category:
            profile.category = category
            profile.save()

        # Validación de contraseña
        if password1 or password2:
            if password1 != password2:
                messages.error(request, "Las contraseñas no coinciden.")
                return redirect('edit_profile')

            # Solo cambiamos la contraseña si ambas están llenas
            if password1 and password2:
                user.set_password(password1)
                user.save()
                update_session_auth_hash(request, user)  # Evita logout automático
                messages.success(request, "Contraseña actualizada correctamente.")
            elif password1 or password2:
                messages.warning(request, "Debes escribir la misma contraseña en ambos campos.")

        else:
            user.save()
            messages.success(request, "Datos actualizados correctamente.")

        return redirect('profile')

    else:
        profile = request.user.userprofile
        return render(request, 'core/edit_profile.html', {
            'user': request.user,
            'profile': profile,
            'categories': ProfessionalCategory.choices
        })