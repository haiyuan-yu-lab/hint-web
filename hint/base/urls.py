from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("downloads", views.downloads, name="downloads"),
    path("faq", views.faq, name="faq"),
    path("viewer", views.home, name="viewer"),
]
