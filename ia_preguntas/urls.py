"""
URL configuration for ia_preguntas project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path, include
from core.views import upload_topics_view  # 👈 Importa tu vista aquí
from django.contrib import admin

urlpatterns = [
     # 👇 Nueva ruta personalizada ANTES de 'include("core.urls")'
    path('admin/upload-topics/', upload_topics_view, name='upload_topics'),
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
]
