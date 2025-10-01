# moderation/urls.py
from django.urls import path
from . import views

app_name = "moderation"

urlpatterns = [
    path("report/<int:pk>", views.report_image, name="report"),
]
