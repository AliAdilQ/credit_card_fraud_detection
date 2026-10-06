from django.urls import path
from . import views

app_name = "detection"
urlpatterns = [
    path("", views.home, name="home"), path("predict/", views.predict, name="predict"),
    path("result/<uuid:transaction_id>/", views.result, name="result"),
    path("dashboard/", views.dashboard, name="dashboard"), path("transactions/", views.transactions, name="transactions"),
    path("transactions/export/", views.export_transactions, name="export"), path("about/", views.about, name="about"),
]
