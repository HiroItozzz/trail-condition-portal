from django.urls import path

from . import views

urlpatterns = [
    # 一覧画面: /
    path("", views.trail_list, name="trail-list"),
    # 詳細画面: /1/ や /2/ など
    # <int:pk> 部分が views.py の pk という引数に渡されます
    path("<int:pk>/", views.condition_detail, name="condition-detail"),
]
