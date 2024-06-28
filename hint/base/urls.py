from django.urls import path
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("download", views.download, name="download"),
    path("old-versions", views.old_versions, name="old-versions"),
    path("download-raw/<hint_version>/<filename>",
         views.download_raw,
         name="donwload-raw"),
    path("faq", views.faq, name="faq"),
    path("network-viewer", views.network_viewer, name="network-viewer"),
    path("interactions", views.interaction_load_more, name="interactions"),
    path("interaction-evidence/<int:interaction_id>",
         views.interaction_evidence,
         name="interaction-evidence"),
    path("network-download",
         views.interaction_stream_download,
         name="network-download"),
    path("search-proteins", views.search_proteins, name="search-proteins"),
]

urlpatterns += staticfiles_urlpatterns()
