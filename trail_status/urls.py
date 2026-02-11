from django.urls import path
from django.views.generic import TemplateView

from . import views

urlpatterns = [
    # 一覧画面: /
    path("", views.trail_list, name="trail-list"),
    # 詳細画面: /trail/1/ や /trail/2/ など
    path("trails/<int:pk>/", views.trail_detail, name="trail-detail"),
    # このサイトについて
    path("about/", TemplateView.as_view(template_name="about.html"), name="about"),
    # サイトポリシー
    path("site-policy/", TemplateView.as_view(template_name="site-policy.html"), name="site-policy"),
    # 情報源一覧
    path("sources/", views.sources_list, name="sources-list"),
    # リダイレクト
    path("trails", views.trail_redirect, name="trail-redirect"),
    path("blogs/", views.blogs_list, name="blogs-list"),
]
