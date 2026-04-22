from django.urls import path
from django.views.generic import TemplateView

from . import views

urlpatterns = [
    # 一覧画面: /
    path("", views.trail_list, name="trail-list"),
    # 詳細画面: /trail/1/ や /trail/2/ など
    path("trails/<int:pk>/", views.trail_detail, name="trail-detail"),
    # 情報源一覧
    path("sources/", views.SourceListView.as_view(), name="sources-list"),
    # リダイレクト
    path("trails", views.trail_redirect, name="trail-redirect"),
    # 巡視ブログ一覧
    path("blogs/", views.blog_list, name="blog-list"),
]
