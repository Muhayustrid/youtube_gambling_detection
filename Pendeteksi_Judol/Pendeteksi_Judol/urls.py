"""
URL configuration for Pendeteksi_Judol project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
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
from django.contrib import admin
from django.urls import path, include
from machine_learning import views
from akun.views_oauth import oauth_start, oauth_callback
from akun.views_moderate import moderate_comments
from akun.views import revoke_and_logout_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.analyze, name='analyze'),
    path('cekpreprocess/', views.home, name='home'),
    path("oauth/start/", oauth_start, name="oauth_start"),
    path("oauth/callback/", oauth_callback, name="oauth_callback"),
    path("moderate/", moderate_comments, name="moderate_comments"),
    path("logout/", revoke_and_logout_view, name="logout_view")
]
