from django.contrib import admin
from django.urls import include, path

urlpatterns = [path("admin/", admin.site.urls), path("", include("detection.urls"))]
handler404 = "detection.views.not_found"
handler500 = "detection.views.server_error"
