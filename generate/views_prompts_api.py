from __future__ import annotations

from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import transaction
from django.http import HttpRequest, JsonResponse
from django.utils.text import slugify
from django.views.decorators.http import require_POST

from .models import PromptCategory, CategoryPrompt


def _b(val, default: bool = False) -> bool:
    if val is None:
        return default
    return str(val).strip().lower() in {"1", "true", "yes", "on"}


def _is_staff(user) -> bool:
    return bool(getattr(user, "is_authenticated", False) and getattr(user, "is_staff", False))


# ===========================
# PromptCategory CRUD (staff)
# ===========================

@login_required
@user_passes_test(_is_staff)
@require_POST
@transaction.atomic
def pc_create(request: HttpRequest) -> JsonResponse:
    """
    Создать категорию промптов.
    POST multipart/form-data:
      - name (обязательно)
      - [slug]
      - [description]
      - [order]
      - [is_active=1|0]
      - [image] (file)
    """
    name = (request.POST.get("name") or "").strip()
    if not name:
        return JsonResponse({"ok": False, "error": "name is required"}, status=400)

    base = slugify((request.POST.get("slug") or name).strip() or "cat") or "cat"
    slug_val = base
    i = 2
    while PromptCategory.objects.filter(slug=slug_val).exists():
        slug_val = f"{base}-{i}"
        i += 1

    description = (request.POST.get("description") or "").strip()
    is_active = _b(request.POST.get("is_active"), True)
    try:
        order = int(request.POST.get("order") or 0)
    except Exception:
        order = 0

    obj = PromptCategory(
        name=name,
        slug=slug_val,
        description=description,
        order=order,
        is_active=is_active,
    )
    image = request.FILES.get("image")
    if image:
        obj.image = image
    obj.save()

    image_url = None
    try:
        if obj.image and obj.image.url:
            image_url = obj.image.url
    except Exception:
        image_url = None

    return JsonResponse(
        {
            "ok": True,
            "id": obj.id,
            "name": obj.name,
            "slug": obj.slug,
            "is_active": obj.is_active,
            "order": obj.order,
            "image": image_url,
        },
        status=201,
    )


@login_required
@user_passes_test(_is_staff)
@require_POST
@transaction.atomic
def pc_update(request: HttpRequest, pk: int) -> JsonResponse:
    """
    Обновить категорию промптов.
    Допускаются частичные обновления. Для смены изображения передайте файл 'image'.
    """
    try:
        obj = PromptCategory.objects.get(pk=pk)
    except PromptCategory.DoesNotExist:
        return JsonResponse({"ok": False, "error": "category not found"}, status=404)

    name = request.POST.get("name")
    slug_in = request.POST.get("slug")
    description = request.POST.get("description")
    order = request.POST.get("order")
    is_active = request.POST.get("is_active")
    image = request.FILES.get("image")

    updates = []

    if name is not None:
        obj.name = name.strip() or obj.name
        updates.append("name")

    if slug_in is not None:
        new_slug = slugify(slug_in.strip() or obj.name) or obj.slug
        if new_slug != obj.slug and PromptCategory.objects.filter(slug=new_slug).exclude(pk=obj.pk).exists():
            return JsonResponse({"ok": False, "error": "slug already exists"}, status=400)
        obj.slug = new_slug
        updates.append("slug")

    if description is not None:
        obj.description = description.strip()
        updates.append("description")

    if order is not None:
        try:
            obj.order = int(order)
            updates.append("order")
        except Exception:
            pass

    if is_active is not None:
        obj.is_active = _b(is_active, obj.is_active)
        updates.append("is_active")

    if image is not None:
        obj.image = image
        updates.append("image")

    if updates:
        obj.save(update_fields=list(set(updates)))

    return JsonResponse({"ok": True})


@login_required
@user_passes_test(_is_staff)
@require_POST
@transaction.atomic
def pc_delete(request: HttpRequest, pk: int) -> JsonResponse:
    try:
        obj = PromptCategory.objects.get(pk=pk)
    except PromptCategory.DoesNotExist:
        return JsonResponse({"ok": False, "error": "category not found"}, status=404)
    obj.delete()
    return JsonResponse({"ok": True})


# ===========================
# CategoryPrompt CRUD (staff)
# ===========================

@login_required
@user_passes_test(_is_staff)
@require_POST
@transaction.atomic
def cp_create(request: HttpRequest) -> JsonResponse:
    """
    Создать промпт в категории.
    POST:
      - category_id (обязательно)
      - title (обязательно)
      - prompt_text (обязательно)
      - [prompt_en]
      - [order]
      - [is_active=1|0]
    """
    try:
        category_id = int(request.POST.get("category_id") or 0)
    except Exception:
        category_id = 0

    title = (request.POST.get("title") or "").strip()
    text = (request.POST.get("prompt_text") or "").strip()
    if not (category_id and title and text):
        return JsonResponse({"ok": False, "error": "category_id, title, prompt_text are required"}, status=400)

    try:
        category = PromptCategory.objects.get(pk=category_id)
    except PromptCategory.DoesNotExist:
        return JsonResponse({"ok": False, "error": "category not found"}, status=404)

    prompt_en = (request.POST.get("prompt_en") or "").strip()
    try:
        order = int(request.POST.get("order") or 0)
    except Exception:
        order = 0
    is_active = _b(request.POST.get("is_active"), True)

    p = CategoryPrompt.objects.create(
        category=category,
        title=title,
        prompt_text=text,
        prompt_en=prompt_en,
        order=order,
        is_active=is_active,
    )

    return JsonResponse(
        {
            "ok": True,
            "id": p.id,
            "title": p.title,
            "prompt_text": p.prompt_text,
            "prompt_en": p.prompt_en,
            "order": p.order,
            "is_active": p.is_active,
        },
        status=201,
    )


@login_required
@user_passes_test(_is_staff)
@require_POST
@transaction.atomic
def cp_update(request: HttpRequest, pk: int) -> JsonResponse:
    """
    Обновить промпт.
    POST: [title], [prompt_text], [prompt_en], [order], [is_active=1|0], [category_id]
    """
    try:
        p = CategoryPrompt.objects.get(pk=pk)
    except CategoryPrompt.DoesNotExist:
        return JsonResponse({"ok": False, "error": "prompt not found"}, status=404)

    title = request.POST.get("title")
    text = request.POST.get("prompt_text")
    en = request.POST.get("prompt_en")
    order = request.POST.get("order")
    is_active = request.POST.get("is_active")
    category_id = request.POST.get("category_id")

    updates = []

    if title is not None:
        p.title = title.strip() or p.title
        updates.append("title")
    if text is not None:
        p.prompt_text = text.strip()
        updates.append("prompt_text")
    if en is not None:
        p.prompt_en = en.strip()
        updates.append("prompt_en")
    if order is not None:
        try:
            p.order = int(order)
            updates.append("order")
        except Exception:
            pass
    if is_active is not None:
        p.is_active = _b(is_active, p.is_active)
        updates.append("is_active")
    if category_id is not None:
        try:
            cat = PromptCategory.objects.get(pk=int(category_id))
            p.category = cat
            updates.append("category")
        except Exception:
            pass

    if updates:
        p.save(update_fields=list(set(updates)))

    return JsonResponse({"ok": True})


@login_required
@user_passes_test(_is_staff)
@require_POST
@transaction.atomic
def cp_delete(request: HttpRequest, pk: int) -> JsonResponse:
    try:
        p = CategoryPrompt.objects.get(pk=pk)
    except CategoryPrompt.DoesNotExist:
        return JsonResponse({"ok": False, "error": "prompt not found"}, status=404)
    p.delete()
    return JsonResponse({"ok": True})
