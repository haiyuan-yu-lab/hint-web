from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("download", views.download, name="download"),
    path("faq", views.faq, name="faq"),
    path("network-viewer", views.network_viewer, name="network-viewer"),
    path("search-proteins", views.search_proteins, name="search-proteins"),
    path("old-versions", views.old_versions, name="old-versions"),
]
