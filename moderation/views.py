# moderation/views.py
from django.http import HttpResponse, HttpResponseNotFound, HttpResponseServerError
from django.shortcuts import get_object_or_404
from django.apps import apps

def report_image(request, pk: int):
    """
    Безопасно получаем модель Image из ПРИЛОЖЕНИЯ gallery.
    Если модели нет — не роняем сервер на импорте, а отвечаем 500/404 при обращении.
    """
    try:
        Image = apps.get_model('gallery', 'Image')
    except LookupError:
        return HttpResponseServerError("Model 'Image' not found in app 'gallery'")

    if Image is None:
        return HttpResponseServerError("Model 'Image' not found in app 'gallery'")

    obj = get_object_or_404(Image, pk=pk)
    # тут делай логику репорта/жалобы
    return HttpResponse("OK")
