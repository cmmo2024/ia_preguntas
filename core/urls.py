from django.urls import path
from . import views
from django.http import JsonResponse

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('ajax/load-topics/', views.load_topics, name='ajax_load_topics'),
]