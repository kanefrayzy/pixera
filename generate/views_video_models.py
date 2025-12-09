"""
Views for Video Model Configuration Management
Provides frontend interface for admins to manage video models
"""
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Q
from django.core.paginator import Paginator

from .models_video import VideoModelConfiguration
from .forms_video_model import VideoModelConfigurationForm, VideoModelQuickEditForm


@staff_member_required
def video_models_list(request):
    """
    List all video model configurations with filtering and search
    """
    # Get filter parameters
    category = request.GET.get('category', '')
    is_active = request.GET.get('is_active', '')
    is_premium = request.GET.get('is_premium', '')
    search = request.GET.get('search', '')

    # Base queryset
    models = VideoModelConfiguration.objects.all()

    # Apply filters
    if category:
        models = models.filter(category=category)

    if is_active:
        models = models.filter(is_active=is_active == 'true')

    if is_premium:
        models = models.filter(is_premium=is_premium == 'true')

    if search:
        models = models.filter(
            Q(name__icontains=search) |
            Q(model_id__icontains=search) |
            Q(description__icontains=search)
        )

    # Order by category and order
    models = models.order_by('category', 'order', 'name')

    # Pagination
    paginator = Paginator(models, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # Get categories for filter
    categories = VideoModelConfiguration.Category.choices

    context = {
        'page_obj': page_obj,
        'categories': categories,
        'current_category': category,
        'current_is_active': is_active,
        'current_is_premium': is_premium,
        'search_query': search,
        'total_count': models.count(),
    }

    return render(request, 'generate/video_models_list.html', context)


@staff_member_required
def video_model_create(request):
    """
    Create a new video model configuration
    """
    if request.method == 'POST':
        form = VideoModelConfigurationForm(request.POST, request.FILES)
        if form.is_valid():
            model = form.save()
            messages.success(request, f'Модель "{model.name}" успешно создана!')
            return redirect('generate:video_models_list')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме.')
    else:
        form = VideoModelConfigurationForm()

    context = {
        'form': form,
        'action': 'create',
        'title': 'Создать новую модель',
    }

    return render(request, 'generate/video_model_form.html', context)


@staff_member_required
def video_model_edit(request, pk):
    """
    Edit an existing video model configuration
    """
    model = get_object_or_404(VideoModelConfiguration, pk=pk)

    if request.method == 'POST':
        form = VideoModelConfigurationForm(request.POST, request.FILES, instance=model)
        if form.is_valid():
            model = form.save()
            messages.success(request, f'Модель "{model.name}" успешно обновлена!')
            return redirect('generate:video_models_list')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме.')
    else:
        form = VideoModelConfigurationForm(instance=model)

    context = {
        'form': form,
        'model': model,
        'action': 'edit',
        'title': f'Редактировать: {model.name}',
    }

    return render(request, 'generate/video_model_form.html', context)


@staff_member_required
@require_http_methods(["POST"])
def video_model_delete(request, pk):
    """
    Delete a video model configuration
    """
    model = get_object_or_404(VideoModelConfiguration, pk=pk)
    model_name = model.name

    try:
        model.delete()
        messages.success(request, f'Модель "{model_name}" успешно удалена!')
    except Exception as e:
        messages.error(request, f'Ошибка при удалении модели: {str(e)}')

    return redirect('generate:video_models_list')


@staff_member_required
def video_model_detail(request, pk):
    """
    View detailed information about a video model configuration
    """
    model = get_object_or_404(VideoModelConfiguration, pk=pk)

    # Get configuration summary
    config_summary = model.get_configuration_summary()

    context = {
        'model': model,
        'config_summary': config_summary,
    }

    return render(request, 'generate/video_model_detail.html', context)


@staff_member_required
@require_http_methods(["POST"])
def video_model_toggle_active(request, pk):
    """
    Toggle active status of a video model
    """
    model = get_object_or_404(VideoModelConfiguration, pk=pk)
    model.is_active = not model.is_active
    model.save(update_fields=['is_active'])

    status = 'активирована' if model.is_active else 'деактивирована'
    messages.success(request, f'Модель "{model.name}" {status}!')

    return redirect('generate:video_models_list')


@staff_member_required
@require_http_methods(["POST"])
def video_model_duplicate(request, pk):
    """
    Duplicate an existing video model configuration
    """
    original = get_object_or_404(VideoModelConfiguration, pk=pk)

    # Create a copy
    duplicate = VideoModelConfiguration.objects.get(pk=original.pk)
    duplicate.pk = None
    duplicate.id = None
    duplicate.name = f"{original.name} (копия)"
    duplicate.model_id = f"{original.model_id}_copy"
    duplicate.slug = f"{original.slug}-copy"
    duplicate.is_active = False  # Deactivate copy by default
    duplicate.save()

    messages.success(request, f'Модель "{original.name}" успешно скопирована!')
    return redirect('generate:video_model_edit', pk=duplicate.pk)


@staff_member_required
def video_model_api_config(request, pk):
    """
    Get model configuration as JSON for API/frontend use
    """
    model = get_object_or_404(VideoModelConfiguration, pk=pk)
    config = model.get_configuration_summary()

    return JsonResponse({
        'id': model.pk,
        'name': model.name,
        'model_id': model.model_id,
        'category': model.category,
        'token_cost': model.token_cost,
        'configuration': config,
    })


@staff_member_required
@require_http_methods(["POST"])
def video_model_bulk_action(request):
    """
    Perform bulk actions on multiple models
    """
    action = request.POST.get('action')
    model_ids = request.POST.getlist('model_ids')

    if not model_ids:
        messages.warning(request, 'Не выбрано ни одной модели.')
        return redirect('generate:video_models_list')

    models = VideoModelConfiguration.objects.filter(pk__in=model_ids)
    count = models.count()

    if action == 'activate':
        models.update(is_active=True)
        messages.success(request, f'Активировано моделей: {count}')
    elif action == 'deactivate':
        models.update(is_active=False)
        messages.success(request, f'Деактивировано моделей: {count}')
    elif action == 'delete':
        models.delete()
        messages.success(request, f'Удалено моделей: {count}')
    elif action == 'mark_premium':
        models.update(is_premium=True)
        messages.success(request, f'Отмечено как премиум: {count}')
    elif action == 'unmark_premium':
        models.update(is_premium=False)
        messages.success(request, f'Снята отметка премиум: {count}')
    else:
        messages.error(request, 'Неизвестное действие.')

    return redirect('generate:video_models_list')


@staff_member_required
def video_model_quick_edit(request, pk):
    """
    Quick edit form for common fields (AJAX)
    """
    model = get_object_or_404(VideoModelConfiguration, pk=pk)

    if request.method == 'POST':
        form = VideoModelQuickEditForm(request.POST, instance=model)
        if form.is_valid():
            form.save()
            return JsonResponse({
                'success': True,
                'message': f'Модель "{model.name}" обновлена!'
            })
        else:
            return JsonResponse({
                'success': False,
                'errors': form.errors
            }, status=400)

    form = VideoModelQuickEditForm(instance=model)
    return render(request, 'generate/video_model_quick_edit.html', {
        'form': form,
        'model': model
    })
