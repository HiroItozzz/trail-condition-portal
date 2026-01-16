from django.urls import path
from django.views.generic import TemplateView

from . import views

urlpatterns = [
    # 一覧画面: /
    path("", views.trail_list, name="trail-list"),
    # 詳細画面: /trail/1/ や /trail/2/ など
    path("trails", views.condition_detail, name="condition-detail"),
    # サイトポリシー
    path("site-policy/", TemplateView.as_view(template_name="site-policy.html"), name="site-policy"),
]
