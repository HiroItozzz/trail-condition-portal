from django.urls import path
from django.views.generic import TemplateView

from . import views

urlpatterns = [
    # 一覧画面: /
    path("", views.trail_list, name="trail-list"),
    # 詳細画面: /1/ や /2/ など
    # <int:pk> 部分が views.py の pk という引数に渡されます
    path("<int:pk>/", views.condition_detail, name="condition-detail"),
    # プライバシーポリシー
    path("privacy/", TemplateView.as_view(template_name="privacy.html"), name="privacy"),
]
