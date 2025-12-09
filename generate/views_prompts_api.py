from __future__ import annotations

from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import transaction
from django.http import HttpRequest, JsonResponse
from django.utils.text import slugify
from django.views.decorators.http import require_POST, require_GET

from .models import PromptCategory, CategoryPrompt, PromptSubcategory


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
    try:
        name = (request.POST.get("name") or "").strip()
        if not name:
            return JsonResponse({"ok": False, "error": "Название категории обязательно"}, status=400)

        # Prevent duplicate names (unique constraint) with clear error
        if PromptCategory.objects.filter(name__iexact=name).exists():
            return JsonResponse({"ok": False, "error": f"Категория с названием '{name}' уже существует"}, status=400)

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
    except Exception as e:
        import logging
        logging.error(f"Error creating prompt category: {e}", exc_info=True)
        return JsonResponse({"ok": False, "error": f"Ошибка создания категории: {str(e)}"}, status=500)


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
      - [subcategory_id] (опционально, должен принадлежать category_id)
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

    # optional subcategory
    subcat = None
    try:
        subcat_id = int(request.POST.get("subcategory_id") or 0)
    except Exception:
        subcat_id = 0
    if subcat_id:
        subcat = PromptSubcategory.objects.filter(pk=subcat_id, category=category).first()
        if subcat is None:
            return JsonResponse({"ok": False, "error": "subcategory not found in this category"}, status=404)

    prompt_en = (request.POST.get("prompt_en") or "").strip()
    try:
        order = int(request.POST.get("order") or 0)
    except Exception:
        order = 0
    is_active = _b(request.POST.get("is_active"), True)

    p = CategoryPrompt.objects.create(
        category=category,
        subcategory=subcat,
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
    POST: [title], [prompt_text], [prompt_en], [order], [is_active=1|0], [category_id], [subcategory_id]
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
    subcategory_id = request.POST.get("subcategory_id")

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
    if subcategory_id is not None:
        try:
            sid = int(subcategory_id or 0)
            if sid == 0:
                p.subcategory = None
                updates.append("subcategory")
            else:
                sc = PromptSubcategory.objects.get(pk=sid)
                # ensure consistency: subcategory must belong to same category
                if p.category_id and sc.category_id != p.category_id:
                    return JsonResponse({"ok": False, "error": "subcategory does not belong to prompt category"}, status=400)
                p.subcategory = sc
                updates.append("subcategory")
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
# ===========================
# PromptSubcategory CRUD (staff)
# ===========================

@login_required
@user_passes_test(_is_staff)
@require_POST
@transaction.atomic
def sc_create(request: HttpRequest) -> JsonResponse:
    """
    Создать подкатегорию.
    POST: category_id (int), name (str), [slug], [description], [order], [is_active]
    """
    try:
        cid = int(request.POST.get("category_id") or 0)
    except Exception:
        cid = 0
    name = (request.POST.get("name") or "").strip()
    if not (cid and name):
        return JsonResponse({"ok": False, "error": "category_id and name are required"}, status=400)
    try:
        cat = PromptCategory.objects.get(pk=cid)
    except PromptCategory.DoesNotExist:
        return JsonResponse({"ok": False, "error": "category not found"}, status=404)

    base = slugify((request.POST.get("slug") or name).strip() or "subcat") or "subcat"
    slug_val = base
    i = 2
    while PromptSubcategory.objects.filter(category=cat, slug=slug_val).exists():
        slug_val = f"{base}-{i}"
        i += 1

    desc = (request.POST.get("description") or "").strip()
    try:
        order = int(request.POST.get("order") or 0)
    except Exception:
        order = 0
    is_active = _b(request.POST.get("is_active"), True)

    sc = PromptSubcategory.objects.create(
        category=cat, name=name, slug=slug_val, description=desc, order=order, is_active=is_active
    )
    return JsonResponse({"ok": True, "id": sc.id, "name": sc.name, "slug": sc.slug, "is_active": sc.is_active}, status=201)


@login_required
@user_passes_test(_is_staff)
@require_POST
@transaction.atomic
def sc_update(request: HttpRequest, pk: int) -> JsonResponse:
    """
    Обновить подкатегорию: [name], [slug], [description], [order], [is_active]
    """
    try:
        sc = PromptSubcategory.objects.get(pk=pk)
    except PromptSubcategory.DoesNotExist:
        return JsonResponse({"ok": False, "error": "subcategory not found"}, status=404)

    name = request.POST.get("name")
    slug_in = request.POST.get("slug")
    description = request.POST.get("description")
    order = request.POST.get("order")
    is_active = request.POST.get("is_active")

    updates = []

    if name is not None:
        sc.name = name.strip() or sc.name
        updates.append("name")
    if slug_in is not None:
        new_slug = slugify(slug_in.strip() or sc.name) or sc.slug
        if new_slug != sc.slug and PromptSubcategory.objects.filter(category=sc.category, slug=new_slug).exclude(pk=sc.pk).exists():
            return JsonResponse({"ok": False, "error": "slug already exists"}, status=400)
        sc.slug = new_slug
        updates.append("slug")
    if description is not None:
        sc.description = description.strip()
        updates.append("description")
    if order is not None:
        try:
            sc.order = int(order)
            updates.append("order")
        except Exception:
            pass
    if is_active is not None:
        sc.is_active = _b(is_active, sc.is_active)
        updates.append("is_active")

    if updates:
        sc.save(update_fields=list(set(updates)))

    return JsonResponse({"ok": True})


@login_required
@user_passes_test(_is_staff)
@require_POST
@transaction.atomic
def sc_delete(request: HttpRequest, pk: int) -> JsonResponse:
    """
    Удалить подкатегорию (промпты не удаляем — отвязываем от подкатегории).
    """
    try:
        sc = PromptSubcategory.objects.get(pk=pk)
    except PromptSubcategory.DoesNotExist:
        return JsonResponse({"ok": False, "error": "subcategory not found"}, status=404)

    CategoryPrompt.objects.filter(subcategory=sc).update(subcategory=None)
    sc.delete()
    return JsonResponse({"ok": True})


# ===========================
# Public read APIs
# ===========================

@require_GET
def category_subcategories_api(request: HttpRequest, category_id: int) -> JsonResponse:
    """
    Вернуть список подкатегорий выбранной категории с количеством активных промптов.
    """
    try:
        cat = PromptCategory.objects.get(pk=category_id, is_active=True)
    except PromptCategory.DoesNotExist:
        return JsonResponse({"ok": False, "error": "category not found"}, status=404)

    subs = (
        PromptSubcategory.objects
        .filter(category=cat, is_active=True)
        .order_by("order", "name")
    )
    data = []
    for sc in subs:
        cnt = CategoryPrompt.objects.filter(category=cat, subcategory=sc, is_active=True).count()
        data.append({
            "id": sc.id,
            "name": sc.name,
            "slug": sc.slug,
            "description": sc.description,
            "order": sc.order,
            "is_active": sc.is_active,
            "prompts_count": cnt,
        })

    return JsonResponse({"ok": True, "category": {"id": cat.id, "name": cat.name}, "subcategories": data})


@require_GET
def subcategory_prompts_api(request: HttpRequest, subcategory_id: int) -> JsonResponse:
    """
    Вернуть промпты конкретной подкатегории.
    """
    try:
        sc = PromptSubcategory.objects.select_related("category").get(pk=subcategory_id, is_active=True)
    except PromptSubcategory.DoesNotExist:
        return JsonResponse({"ok": False, "error": "subcategory not found"}, status=404)

    prompts = (
        CategoryPrompt.objects
        .filter(category=sc.category, subcategory=sc, is_active=True)
        .order_by("order", "title")
    )
    items = [{
        "id": p.id,
        "title": p.title,
        "prompt_text": p.prompt_text,
        "prompt_en": p.get_prompt_for_generation(),
        "prompt_en_raw": p.prompt_en,
        "order": p.order,
        "is_active": p.is_active,
    } for p in prompts]

    return JsonResponse({
        "ok": True,
        "subcategory": {"id": sc.id, "name": sc.name, "category_id": sc.category_id},
        "prompts": items
    })
