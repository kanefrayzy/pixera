from django.urls import path
from . import api_views

urlpatterns = [
    path("images/", api_views.ImageListAPI.as_view(), name="images"),
    path("images/<int:pk>/", api_views.ImageDetailAPI.as_view(), name="image-detail"),
]

