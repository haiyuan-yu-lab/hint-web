from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("download", views.download, name="download"),
    path("faq", views.faq, name="faq"),
    path("viewer", views.home, name="viewer"),
]
