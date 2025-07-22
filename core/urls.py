from django.urls import include, path
from . import views
from django.http import JsonResponse
from allauth.account import views as allauth_views  # 👈 Esta es la parte nueva

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
    # Pagos
    path('upgrade/premium/', views.create_payment, name='create_payment'),
    path('pago/exito/', views.payment_success, name='payment_success'),
    path('pago/cancelado/', views.payment_cancelled, name='payment_cancelled'),
    path('accounts/', include('allauth.urls')),  # Rutas automáticas de allauth
    # Opcional: sobrescribir algunas vistas
    #path('accounts/login/', allauth_views.login, name="login"),
    #path('accounts/logout/', allauth_views.logout, name="logout"),
    path('transfermovil/', views.transfermovil_view, name='transfermovil'),
    path('soporte/', views.faq_chatbot, name='faq_chatbot'),
    path('exam/<int:exam_id>/', views.exam_detail, name='exam_detail'),
    path('examen/eliminar/<int:exam_id>/', views.delete_exam, name='delete_exam'),
    path('perfil/editar/', views.edit_profile_view, name='edit_profile'),
    path('subject/delete/<int:subject_id>/', views.delete_subject, name='delete_subject'),
]