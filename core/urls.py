from django.urls import path
from . import views
from django.http import JsonResponse

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('ajax/load-topics/', views.load_topics, name='ajax_load_topics'),
    # 👇 Nuevas rutas
    path('acerca-de/', views.about_view, name='about'),
    path('ayuda/', views.help_view, name='help'),
    # 👇 Nueva ruta para eliminar
    path('conversation/delete/<int:conv_id>/', views.delete_conversation, name='delete_conversation'),
    # 👇 Nuevas rutas para examen
    path('exam/', views.exam_view, name='exam'),
    path('exam/submit/', views.submit_exam, name='submit_exam'),
    path('perfil/', views.profile_view, name='profile'),
]