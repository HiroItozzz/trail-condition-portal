from django.urls import path

from . import views

urlpatterns = [
    path("trail-conditions/", views.ListView.as_view(), name="list"),
    path("trail-conditions/<int:pk>", views.DetailView.as_view(), name="detail"),
    # path("api/areas/{area}/conditions/"),
    # path("api/sources/"),
    # path("api/sources/{id}/conditions/"),
]
