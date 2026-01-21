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
from deteksi.views import index, oauth_start, oauth_callback, revoke_and_logout_view, moderate_comments, home, my_videos_partial, video_saya, comment_detail, get_ai_insight, get_dataset
from .views import privacy_policy, terms_of_service

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', index, name='index'),
    path('get-ai-insight/', get_ai_insight, name='get_ai_insight'),
    path('preproces/', home, name='home'),
    path("oauth/start/", oauth_start, name="oauth_start"),
    path("oauth/callback/", oauth_callback, name="oauth_callback"),
    path("moderate/", moderate_comments, name="moderate_comments"),
    path("logout/", revoke_and_logout_view, name="logout_view"),
    path("privacy/", privacy_policy, name="privacy_policy"),
    path("terms/", terms_of_service, name="terms_of_service"),
    path("my-videos-partial/", my_videos_partial, name="my_videos_partial"),
    path("video-saya/", video_saya, name="video_saya"),
    path("comment/detail/", comment_detail, name="comment_detail"),
    path("getdataset/", get_dataset, name="get_dataset"),
]
