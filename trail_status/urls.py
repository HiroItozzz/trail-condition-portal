from django.urls import path

from . import views

app_name = "trail_status"
urlpatterns = [
    # 一覧画面: /
    path("", views.TrailListView.as_view(), name="trail-list"),
    # 詳細画面: /trail/1/ や /trail/2/ など
    path("trails/<int:pk>/", views.TrailDetailView.as_view(), name="trail-detail"),
    # 情報源一覧
    path("sources/", views.SourceListView.as_view(), name="source-list"),
    # 巡視ブログ一覧
    path("blogs/", views.BlogListView.as_view(), name="blog-list"),
    # プロンプト編集画面
    path("prompt/<int:source_id>/", views.PromptEditView.as_view(), name="prompt-edit"),
    # プロンプトAPI
    path("api/prompt/", views.get_prompt_json, name="temp-prompt-api"),
    path("api/prompt/<int:source_id>/", views.get_prompt_json, name="prompt-api"),
    path("api/prompt/<int:source_id>/post/", views.update_yaml, name="prompt-post-api"),
    # 情報源API
    path("api/source/<int:source_id>/", views.get_data_source, name="source-api"),
]
