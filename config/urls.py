"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
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

import os

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

urlpatterns = [
    path("", include("trail_status.urls")),
    path(os.environ.get("DJANGO_ADMIN_PATH", "admin/"), admin.site.urls),
    path("scheduler/", include("scheduler.urls")),
    # このサイトについて
    path("about/", TemplateView.as_view(template_name="about.html"), name="about"),
    # サイトポリシー
    path("site-policy/", TemplateView.as_view(template_name="site-policy.html"), name="site-policy"),
    # robots.txt
    path("robots.txt", TemplateView.as_view(template_name="robots.txt", content_type="text/plain")),
]

# 開発サーバー用の静的ファイル配信
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
