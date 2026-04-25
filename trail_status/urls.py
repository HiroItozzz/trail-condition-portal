from django.urls import path
from django.views.generic import TemplateView

from . import views

urlpatterns = [
    # 一覧画面: /
    path("", views.TrailListView.as_view(), name="trail-list"),
    # 詳細画面: /trail/1/ や /trail/2/ など
    path("trails/<int:pk>/", views.TrailDetailView.as_view(), name="trail-detail"),
    # 情報源一覧
    path("sources/", views.SourceListView.as_view(), name="source-list"),
    # 巡視ブログ一覧
    path("blogs/", views.BlogListView.as_view(), name="blog-list"),
]
