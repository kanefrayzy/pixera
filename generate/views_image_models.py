"""
Views for Image Model Configuration Management
Admin interface for managing image generation models
"""
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.db import transaction

from .models_image import ImageModelConfiguration
from .forms_image_model import ImageModelConfigurationForm


@staff_member_required
def image_models_list(request):
    """List all image models"""
    models = ImageModelConfiguration.objects.all().order_by('order', 'name')

    context = {
        'models': models,
        'title': 'Управление моделями изображений',
    }

    return render(request, 'generate/image_models_list.html', context)


@staff_member_required
def image_model_create(request):
    """Create new image model"""
    if request.method == 'POST':
        form = ImageModelConfigurationForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                with transaction.atomic():
                    model = form.save()
                    messages.success(request, f'Модель "{model.name}" успешно создана!')
                    return redirect('generate:image_model_detail', pk=model.pk)
            except Exception as e:
                messages.error(request, f'Ошибка при создании модели: {e}')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме')
    else:
        form = ImageModelConfigurationForm()

    context = {
        'form': form,
        'title': 'Создать модель изображений',
        'submit_text': 'Создать модель',
    }

    return render(request, 'generate/image_model_form.html', context)


@staff_member_required
def image_model_edit(request, pk):
    """Edit existing image model"""
    model = get_object_or_404(ImageModelConfiguration, pk=pk)

    if request.method == 'POST':
        form = ImageModelConfigurationForm(request.POST, request.FILES, instance=model)
        if form.is_valid():
            try:
                with transaction.atomic():
                    model = form.save()
                    messages.success(request, f'Модель "{model.name}" успешно обновлена!')
                    return redirect('generate:image_model_detail', pk=model.pk)
            except Exception as e:
                messages.error(request, f'Ошибка при обновлении модели: {e}')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме')
    else:
        form = ImageModelConfigurationForm(instance=model)

    context = {
        'form': form,
        'model': model,
        'title': f'Редактировать: {model.name}',
        'submit_text': 'Сохранить изменения',
    }

    return render(request, 'generate/image_model_form.html', context)


@staff_member_required
def image_model_detail(request, pk):
    """View image model details"""
    model = get_object_or_404(ImageModelConfiguration, pk=pk)

    # Собираем информацию о разрешениях
    resolutions = []
    if getattr(model, 'resolution_512x512', False):
        resolutions.append('512×512')
    if getattr(model, 'resolution_768x768', False):
        resolutions.append('768×768')
    if getattr(model, 'resolution_1024x1024', False):
        resolutions.append('1024×1024')
    if getattr(model, 'resolution_1024x768', False):
        resolutions.append('1024×768')
    if getattr(model, 'resolution_768x1024', False):
        resolutions.append('768×1024')
    if getattr(model, 'resolution_1536x1536', False):
        resolutions.append('1536×1536')
    if getattr(model, 'resolution_2048x2048', False):
        resolutions.append('2048×2048')

    config_summary = {
        'resolutions': resolutions,
    }

    context = {
        'model': model,
        'title': model.name,
        'config_summary': config_summary,
    }

    return render(request, 'generate/image_model_detail.html', context)


@staff_member_required
def image_model_delete(request, pk):
    """Delete image model"""
    model = get_object_or_404(ImageModelConfiguration, pk=pk)

    if request.method == 'POST':
        model_name = model.name
        try:
            model.delete()
            messages.success(request, f'Модель "{model_name}" успешно удалена!')
            return redirect('generate:image_models_list')
        except Exception as e:
            messages.error(request, f'Ошибка при удалении модели: {e}')
            return redirect('generate:image_model_detail', pk=pk)

    context = {
        'model': model,
        'title': f'Удалить модель: {model.name}',
    }

    return render(request, 'generate/image_model_delete.html', context)


@staff_member_required
def image_model_toggle_active(request, pk):
    """Toggle model active status"""
    model = get_object_or_404(ImageModelConfiguration, pk=pk)

    model.is_active = not model.is_active
    model.save(update_fields=['is_active'])

    status = 'активирована' if model.is_active else 'деактивирована'
    messages.success(request, f'Модель "{model.name}" {status}!')

    return redirect('generate:image_models_list')


@staff_member_required
def image_model_duplicate(request, pk):
    """Duplicate an existing image model"""
    if request.method != 'POST':
        return redirect('generate:image_model_detail', pk=pk)

    original = get_object_or_404(ImageModelConfiguration, pk=pk)

    try:
        with transaction.atomic():
            # Create a copy
            duplicate = ImageModelConfiguration.objects.get(pk=original.pk)
            duplicate.pk = None
            duplicate.id = None
            duplicate.name = f"{original.name} (копия)"
            duplicate.slug = None  # Will be auto-generated
            duplicate.is_active = False  # Deactivate by default
            duplicate.save()

            messages.success(request, f'Модель "{original.name}" успешно дублирована!')
            return redirect('generate:image_model_edit', pk=duplicate.pk)
    except Exception as e:
        messages.error(request, f'Ошибка при дублировании модели: {e}')
        return redirect('generate:image_model_detail', pk=pk)
