from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.urls import reverse
from django.core.paginator import Paginator
from django.db.models import Q
from django.views.decorators.http import require_POST
import json

from .models_slider import SliderExample
from .models_slider_video import VideoSliderExample
from generate.models import ShowcaseVideo
from .forms_slider import (
    SliderExampleForm,
    BulkImportForm,
    BulkExportForm,
    SliderExampleFilterForm
)
from .forms_slider_video import VideoSliderExampleForm


@staff_member_required
def slider_examples_list(request):
    """Список всех примеров слайдера"""

    # Фильтрация
    filter_form = SliderExampleFilterForm(request.GET)
    examples = SliderExample.objects.all()

    if filter_form.is_valid():
        title = filter_form.cleaned_data.get('title')
        is_active = filter_form.cleaned_data.get('is_active')

        if title:
            examples = examples.filter(
                Q(title__icontains=title) | Q(description__icontains=title)
            )

        if is_active:
            examples = examples.filter(is_active=is_active == '1')

    examples = examples.order_by('order', 'json_id')

    # Пагинация
    paginator = Paginator(examples, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Video list (VideoSliderExample) with the same filters
    videos = VideoSliderExample.objects.all()
    if filter_form.is_valid():
        if title:
            videos = videos.filter(Q(title__icontains=title) | Q(prompt__icontains=title))
        if is_active:
            videos = videos.filter(is_active=is_active == '1')
    videos = videos.order_by('order', '-created_at')
    v_paginator = Paginator(videos, 10)
    v_page_number = request.GET.get('vpage')
    vpage_obj = v_paginator.get_page(v_page_number)
    videos_total = videos.count()

    context = {
        'page_obj': page_obj,
        'vpage_obj': vpage_obj,
        'videos_total': videos_total,
        'filter_form': filter_form,
        'total_count': examples.count(),
    }

    return render(request, 'dashboard/slider_examples/list.html', context)


@staff_member_required
def slider_example_create(request):
    """Создание нового примера"""

    if request.method == 'POST':
        form = SliderExampleForm(request.POST, request.FILES)
        if form.is_valid():
            example = form.save()
            messages.success(request, f'Пример "{example.title}" успешно создан')
            return redirect('dashboard:slider:list')
    else:
        form = SliderExampleForm()

    context = {
        'form': form,
        'title': 'Создать новый пример',
        'action': 'create'
    }

    return render(request, 'dashboard/slider_examples/form.html', context)


@staff_member_required
def slider_example_edit(request, pk):
    """Редактирование примера"""

    example = get_object_or_404(SliderExample, pk=pk)

    if request.method == 'POST':
        form = SliderExampleForm(request.POST, request.FILES, instance=example)
        if form.is_valid():
            example = form.save()
            messages.success(request, f'Пример "{example.title}" успешно обновлен')
            return redirect('dashboard:slider:list')
    else:
        form = SliderExampleForm(instance=example)

    context = {
        'form': form,
        'example': example,
        'title': f'Редактировать: {example.title}',
        'action': 'edit'
    }

    return render(request, 'dashboard/slider_examples/form.html', context)


@staff_member_required
def slider_example_delete(request, pk):
    """Удаление примера"""

    example = get_object_or_404(SliderExample, pk=pk)

    if request.method == 'POST':
        title = example.title
        example.delete()
        messages.success(request, f'Пример "{title}" успешно удален')
        return redirect('dashboard:slider:list')

    context = {
        'example': example,
        'title': f'Удалить пример: {example.title}'
    }

    return render(request, 'dashboard/slider_examples/delete.html', context)


@staff_member_required
def slider_examples_import(request):
    """Импорт данных из JSON файла"""

    if request.method == 'POST':
        form = BulkImportForm(request.POST)
        if form.is_valid():
            success, message = SliderExample.load_from_json()
            if success:
                messages.success(request, f'Импорт завершен: {message}')
            else:
                messages.error(request, f'Ошибка импорта: {message}')
            return redirect('dashboard:slider:list')
    else:
        form = BulkImportForm()

    context = {
        'form': form,
        'title': 'Импорт из JSON файла',
        'json_path': SliderExample.get_json_file_path()
    }

    return render(request, 'dashboard/slider_examples/import.html', context)


@staff_member_required
def slider_examples_export(request):
    """Экспорт данных в JSON файл"""

    if request.method == 'POST':
        form = BulkExportForm(request.POST)
        if form.is_valid():
            success, message = SliderExample.export_to_json()
            if success:
                messages.success(request, f'Экспорт завершен: {message}')
            else:
                messages.error(request, f'Ошибка экспорта: {message}')
            return redirect('dashboard:slider:list')
    else:
        form = BulkExportForm()

    active_count = SliderExample.objects.filter(is_active=True).count()

    context = {
        'form': form,
        'title': 'Экспорт в JSON файл',
        'active_count': active_count,
        'json_path': SliderExample.get_json_file_path()
    }

    return render(request, 'dashboard/slider_examples/export.html', context)


@staff_member_required
@require_POST
def slider_example_toggle_active(request, pk):
    """AJAX переключение активности примера"""

    example = get_object_or_404(SliderExample, pk=pk)
    example.is_active = not example.is_active
    example.save()

    return JsonResponse({
        'success': True,
        'is_active': example.is_active,
        'message': f'Пример {"активирован" if example.is_active else "деактивирован"}'
    })


@staff_member_required
@require_POST
def slider_examples_reorder(request):
    """AJAX изменение порядка примеров"""

    try:
        data = json.loads(request.body)
        orders = data.get('orders', [])

        for item in orders:
            example_id = item.get('id')
            new_order = item.get('order')

            if example_id and new_order is not None:
                SliderExample.objects.filter(pk=example_id).update(order=new_order)

        # Экспортируем изменения в JSON
        SliderExample.export_to_json()

        return JsonResponse({
            'success': True,
            'message': 'Порядок примеров обновлен'
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Ошибка: {str(e)}'
        })


@staff_member_required
def slider_example_preview(request, pk):
    """Предпросмотр примера"""

    example = get_object_or_404(SliderExample, pk=pk)

    # Формируем данные для предпросмотра в том же формате, что и в JSON
    preview_data = {
        "id": example.json_id,
        "title": example.title,
        "prompt": example.prompt,
        "image": example.image.url if example.image else "/static/img/default.png",
        "description": example.description,
        "alt": example.alt,
        "settings": {
            "steps": example.steps,
            "cfg": example.cfg,
            "ratio": example.ratio,
            "seed": example.seed
        }
    }

    context = {
        'example': example,
        'preview_data': preview_data,
        'title': f'Предпросмотр: {example.title}'
    }

    return render(request, 'dashboard/slider_examples/preview.html', context)


@staff_member_required
def video_slider_example_create(request):
    """Создание нового видео-примера"""
    if request.method == 'POST':
        form = VideoSliderExampleForm(request.POST, request.FILES)
        if form.is_valid():
            example = form.save()
            messages.success(request, f'Видео-пример "{example.title}" успешно создан')
            return redirect('dashboard:slider:list')
    else:
        form = VideoSliderExampleForm()

    context = {
        'form': form,
        'title': 'Создать новый видео-пример',
        'action': 'create'
    }
    return render(request, 'dashboard/slider_examples/video_form.html', context)


@staff_member_required
def video_slider_example_edit(request, pk):
    """Редактирование видео-примера"""
    example = get_object_or_404(VideoSliderExample, pk=pk)
    if request.method == 'POST':
        form = VideoSliderExampleForm(request.POST, request.FILES, instance=example)
        if form.is_valid():
            example = form.save()
            messages.success(request, f'Видео-пример "{example.title}" успешно обновлен')
            return redirect('dashboard:slider:list')
    else:
        form = VideoSliderExampleForm(instance=example)

    context = {
        'form': form,
        'example': example,
        'title': f'Редактировать видео: {example.title}',
        'action': 'edit'
    }
    return render(request, 'dashboard/slider_examples/video_form.html', context)


@staff_member_required
def video_slider_example_delete(request, pk):
    """Удаление видео-примера"""
    example = get_object_or_404(VideoSliderExample, pk=pk)
    if request.method == 'POST':
        title = example.title
        example.delete()
        messages.success(request, f'Видео-пример "{title}" успешно удален')
        return redirect('dashboard:slider:list')

    context = {
        'example': example,
        'title': f'Удалить видео-пример: {example.title}'
    }
    return render(request, 'dashboard/slider_examples/video_delete.html', context)


@staff_member_required
def video_slider_example_preview(request, pk):
    """Предпросмотр видео-примера"""
    example = get_object_or_404(VideoSliderExample, pk=pk)
    preview_data = {
        "id": example.json_id,
        "title": example.title,
        "prompt": example.prompt,
        "video": example.video_src,
        "thumbnail": example.thumbnail.url if example.thumbnail else "",
        "description": example.description,
        "settings": {
            "steps": example.steps,
            "cfg": example.cfg,
            "ratio": example.ratio,
            "seed": example.seed
        }
    }
    context = {
        'example': example,
        'preview_data': preview_data,
        'title': f'Предпросмотр видео: {example.title}'
    }
    return render(request, 'dashboard/slider_examples/video_preview.html', context)


@staff_member_required
@require_POST
def video_slider_example_toggle_active(request, pk):
    """AJAX переключение активности видео-примера"""
    example = get_object_or_404(VideoSliderExample, pk=pk)
    example.is_active = not example.is_active
    example.save()
    return JsonResponse({
        'success': True,
        'is_active': example.is_active,
        'message': f'Видео-пример {"активирован" if example.is_active else "деактивирован"}'
    })


@staff_member_required
@require_POST
def video_slider_examples_reorder(request):
    """AJAX изменение порядка видео-примеров"""
    try:
        data = json.loads(request.body)
        orders = data.get('orders', [])
        for item in orders:
            example_id = item.get('id')
            new_order = item.get('order')
            if example_id and new_order is not None:
                VideoSliderExample.objects.filter(pk=example_id).update(order=new_order)

        # Экспортируем изменения в JSON
        VideoSliderExample.export_to_json()

        return JsonResponse({
            'success': True,
            'message': 'Порядок видео-примеров обновлен'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Ошибка: {str(e)}'
        })
