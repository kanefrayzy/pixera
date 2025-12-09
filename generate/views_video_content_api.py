"""
API views for managing video prompt categories and showcase examples
"""
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import json
import logging
from django.utils.text import slugify
import os
import tempfile
import subprocess
from django.utils import timezone
from django.core.files import File

from .models import VideoPromptCategory, VideoPrompt, ShowcaseVideo, VideoPromptSubcategory

def _b(val, default=True) -> bool:
    if val is None:
        return default
    return str(val).strip().lower() in {"1", "true", "yes", "on"}

logger = logging.getLogger(__name__)

def _save_optimized_mp4(upload, subdir: str = "showcase_videos") -> str:
    """
    Save uploaded MP4 optimized for web playback:
    - H.264/AAC, CRF=28, preset=veryfast
    - Scale down to max width 1280, keep aspect
    - movflags +faststart for progressive startup
    Returns public URL from default_storage.
    Fallback to original if ffmpeg is not available.
    """
    base = slugify(getattr(upload, "name", "video").rsplit(".", 1)[0])[:60] or "video"
    tmp_in = None
    tmp_out = None
    try:
        fd, tmp_in = tempfile.mkstemp(suffix=".mp4")
        with os.fdopen(fd, "wb") as fh:
            for chunk in upload.chunks():
                fh.write(chunk)
        tmp_out = tempfile.mktemp(suffix="-opt.mp4")

        cmd = [
            "ffmpeg", "-y", "-i", tmp_in,
            "-vf", "scale='min(1280,iw)':-2",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "28",
            "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            tmp_out,
        ]
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            final_path = tmp_out if os.path.exists(tmp_out) and os.path.getsize(tmp_out) > 0 else tmp_in
        except Exception:
            final_path = tmp_in

        dst_dir = f"{subdir}/{timezone.now():%Y/%m}/"
        filename = f"{base}.mp4"
        storage_name = default_storage.generate_filename(dst_dir + filename)
        with open(final_path, "rb") as fobj:
            storage_name = default_storage.save(storage_name, File(fobj))
        return default_storage.url(storage_name)
    finally:
        try:
            if tmp_in and os.path.exists(tmp_in):
                os.remove(tmp_in)
        except Exception:
            pass
        try:
            if tmp_out and os.path.exists(tmp_out):
                os.remove(tmp_out)
        except Exception:
            pass


# ============================================================================
# Video Prompt Categories API
# ============================================================================

@require_http_methods(["GET"])
def list_video_categories(request):
    """List all video prompt categories - public endpoint"""
    mode = request.GET.get('mode', 't2v')  # i2v or t2v

    categories = VideoPromptCategory.objects.filter(
        is_active=True,
        mode=mode
    ).order_by('order')

    data = [{
        'id': cat.id,
        'name': cat.name,
        'slug': cat.slug,
        'description': cat.description,
        'image_url': cat.image.url if cat.image else None,
        'order': cat.order,
        'prompts_count': cat.active_prompts_count,
        'mode': cat.mode,
    } for cat in categories]

    return JsonResponse({'categories': data})


@staff_member_required
@csrf_exempt
@require_http_methods(["POST"])
def create_video_category(request):
    """Create a new video prompt category"""
    try:
        name = (request.POST.get('name') or '').strip()
        description = (request.POST.get('description') or '').strip()
        order = int(request.POST.get('order', 0))
        mode = (request.POST.get('mode') or 't2v').strip() or 't2v'
        is_active = _b(request.POST.get('is_active', '1'))
        image = request.FILES.get('image')

        if not name:
            return JsonResponse({'error': 'Name is required'}, status=400)

        # Friendly handling for duplicate name: upsert existing (staff-only)
        existing = VideoPromptCategory.objects.filter(name__iexact=name).first()
        if existing:
            existing.description = description
            existing.order = order
            existing.mode = mode
            existing.is_active = is_active
            if image:
                existing.image = image
            existing.save()
            return JsonResponse({
                'success': True,
                'category': {
                    'id': existing.id,
                    'name': existing.name,
                    'slug': existing.slug,
                    'description': existing.description,
                    'image_url': existing.image.url if existing.image else None,
                    'order': existing.order,
                    'mode': existing.mode,
                }
            })

        # Generate unique slug (avoid UNIQUE constraint failure)
        base = slugify((request.POST.get('slug') or name) or 'cat') or 'cat'
        slug_val = base[:100]
        i = 2
        while VideoPromptCategory.objects.filter(slug=slug_val).exists():
            slug_val = f"{base}-{i}"[:100]
            i += 1

        category = VideoPromptCategory.objects.create(
            name=name,
            slug=slug_val,
            description=description,
            order=order,
            mode=mode,
            is_active=is_active
        )

        if image:
            category.image = image
            category.save(update_fields=['image'])

        return JsonResponse({
            'success': True,
            'category': {
                'id': category.id,
                'name': category.name,
                'slug': category.slug,
                'description': category.description,
                'image_url': category.image.url if category.image else None,
                'order': category.order,
                'mode': category.mode,
            }
        })

    except Exception as e:
        logger.error(f"Error creating video category: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@staff_member_required
@csrf_exempt
@require_http_methods(["POST"])
def update_video_category(request, category_id):
    """Update a video prompt category"""
    try:
        category = VideoPromptCategory.objects.get(id=category_id)

        if 'name' in request.POST:
            category.name = request.POST['name']
        if 'description' in request.POST:
            category.description = request.POST['description']
        if 'order' in request.POST:
            category.order = int(request.POST['order'])
        if 'is_active' in request.POST:
            category.is_active = _b(request.POST['is_active'], category.is_active)
        if 'image' in request.FILES:
            category.image = request.FILES['image']

        category.save()

        return JsonResponse({
            'success': True,
            'category': {
                'id': category.id,
                'name': category.name,
                'slug': category.slug,
                'description': category.description,
                'image_url': category.image.url if category.image else None,
                'order': category.order,
                'mode': category.mode,
            }
        })

    except VideoPromptCategory.DoesNotExist:
        return JsonResponse({'error': 'Category not found'}, status=404)
    except Exception as e:
        logger.error(f"Error updating video category: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@staff_member_required
@csrf_exempt
@require_http_methods(["POST"])
def delete_video_category(request, category_id):
    """Delete a video prompt category"""
    try:
        category = VideoPromptCategory.objects.get(id=category_id)
        category.delete()

        return JsonResponse({'success': True})

    except VideoPromptCategory.DoesNotExist:
        return JsonResponse({'error': 'Category not found'}, status=404)
    except Exception as e:
        logger.error(f"Error deleting video category: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def get_category_prompts(request, category_id):
    """Get all prompts for a specific category"""
    try:
        category = VideoPromptCategory.objects.get(id=category_id)
        prompts = VideoPrompt.objects.filter(
            category=category,
            is_active=True
        ).order_by('order')

        data = [{
            'id': prompt.id,
            'title': prompt.title,
            'prompt_text': prompt.prompt_text,
            'prompt_en': prompt.prompt_en,
            'order': prompt.order,
            'is_active': prompt.is_active,
        } for prompt in prompts]

        return JsonResponse({'prompts': data})

    except VideoPromptCategory.DoesNotExist:
        return JsonResponse({'error': 'Category not found'}, status=404)
    except Exception as e:
        logger.error(f"Error getting category prompts: {e}")
        return JsonResponse({'error': str(e)}, status=500)


# ============================================================================
# Video Prompt Subcategories API
# ============================================================================

@require_http_methods(["GET"])
def video_category_subcategories_api(request, category_id: int):
    """List subcategories for a given video category with active prompts count."""
    try:
        cat = VideoPromptCategory.objects.get(pk=category_id, is_active=True)
    except VideoPromptCategory.DoesNotExist:
        return JsonResponse({"ok": False, "error": "category not found"}, status=404)

    subs = (
        VideoPromptSubcategory.objects
        .filter(category=cat, is_active=True)
        .order_by("order", "name")
    )
    out = []
    for sc in subs:
        cnt = VideoPrompt.objects.filter(category=cat, subcategory=sc, is_active=True).count()
        out.append({
            "id": sc.id,
            "name": sc.name,
            "slug": sc.slug,
            "description": sc.description,
            "order": sc.order,
            "is_active": sc.is_active,
            "prompts_count": cnt,
        })
    return JsonResponse({"ok": True, "category": {"id": cat.id, "name": cat.name}, "subcategories": out})


@require_http_methods(["GET"])
def video_subcategory_prompts_api(request, subcategory_id: int):
    """Return prompts for a given video subcategory."""
    try:
        sc = VideoPromptSubcategory.objects.select_related("category").get(pk=subcategory_id, is_active=True)
    except VideoPromptSubcategory.DoesNotExist:
        return JsonResponse({"ok": False, "error": "subcategory not found"}, status=404)

    prompts = (
        VideoPrompt.objects
        .filter(category=sc.category, subcategory=sc, is_active=True)
        .order_by("order", "title")
    )
    items = [{
        "id": p.id,
        "title": p.title,
        "prompt_text": p.prompt_text,
        "prompt_en": p.prompt_en,
        "order": p.order,
        "is_active": p.is_active,
    } for p in prompts]
    return JsonResponse({"ok": True, "subcategory": {"id": sc.id, "name": sc.name, "category_id": sc.category_id}, "prompts": items})


@staff_member_required
@csrf_exempt
@require_http_methods(["POST"])
def create_video_subcategory(request):
    """
    Create video subcategory for a category.
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
        cat = VideoPromptCategory.objects.get(pk=cid)
    except VideoPromptCategory.DoesNotExist:
        return JsonResponse({"ok": False, "error": "category not found"}, status=404)

    base = slugify((request.POST.get("slug") or name).strip() or "subcat") or "subcat"
    slug_val = base
    i = 2
    while VideoPromptSubcategory.objects.filter(category=cat, slug=slug_val).exists():
        slug_val = f"{base}-{i}"
        i += 1

    desc = (request.POST.get("description") or "").strip()
    try:
        order = int(request.POST.get("order") or 0)
    except Exception:
        order = 0
    is_active = _b(request.POST.get("is_active"), True)

    sc = VideoPromptSubcategory.objects.create(
        category=cat, name=name, slug=slug_val, description=desc, order=order, is_active=is_active
    )
    return JsonResponse({"ok": True, "id": sc.id, "name": sc.name, "slug": sc.slug, "is_active": sc.is_active}, status=201)


@staff_member_required
@csrf_exempt
@require_http_methods(["POST"])
def update_video_subcategory(request, subcategory_id: int):
    """Update video subcategory fields: [name], [slug], [description], [order], [is_active]"""
    try:
        sc = VideoPromptSubcategory.objects.get(pk=subcategory_id)
    except VideoPromptSubcategory.DoesNotExist:
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
        if new_slug != sc.slug and VideoPromptSubcategory.objects.filter(category=sc.category, slug=new_slug).exclude(pk=sc.pk).exists():
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


@staff_member_required
@csrf_exempt
@require_http_methods(["POST"])
def delete_video_subcategory(request, subcategory_id: int):
    """Delete video subcategory (detach prompts)."""
    try:
        sc = VideoPromptSubcategory.objects.get(pk=subcategory_id)
    except VideoPromptSubcategory.DoesNotExist:
        return JsonResponse({"ok": False, "error": "subcategory not found"}, status=404)

    VideoPrompt.objects.filter(subcategory=sc).update(subcategory=None)
    sc.delete()
    return JsonResponse({"ok": True})


# ============================================================================
# Video Prompts API
# ============================================================================

@require_http_methods(["GET"])
def list_video_prompts(request):
    """List all video prompts - public endpoint"""
    category_id = request.GET.get('category_id')

    prompts = VideoPrompt.objects.filter(is_active=True).order_by('order')
    if category_id:
        prompts = prompts.filter(category_id=category_id)

    data = [{
        'id': prompt.id,
        'category_id': prompt.category_id,
        'category_name': prompt.category.name,
        'title': prompt.title,
        'prompt_text': prompt.prompt_text,
        'prompt_en': prompt.prompt_en,
        'order': prompt.order,
    } for prompt in prompts]

    return JsonResponse({'prompts': data})


@staff_member_required
@csrf_exempt
@require_http_methods(["POST"])
def create_video_prompt(request):
    """Create a new video prompt"""
    try:
        category_id = request.POST.get('category_id')
        subcategory_id = request.POST.get('subcategory_id')
        title = request.POST.get('title')
        prompt_text = request.POST.get('prompt_text')
        prompt_en = request.POST.get('prompt_en', '')
        order = int(request.POST.get('order', 0))
        is_active = _b(request.POST.get('is_active', '1'))

        if not all([category_id, title, prompt_text]):
            return JsonResponse({'error': 'Missing required fields'}, status=400)

        subcat = None
        if subcategory_id:
            try:
                subcat = VideoPromptSubcategory.objects.get(pk=int(subcategory_id))
                if subcat.category_id != int(category_id):
                    return JsonResponse({'error': 'subcategory does not belong to category'}, status=400)
            except Exception:
                subcat = None

        prompt = VideoPrompt.objects.create(
            category_id=category_id,
            subcategory=subcat,
            title=title,
            prompt_text=prompt_text,
            prompt_en=prompt_en,
            order=order,
            is_active=is_active
        )

        return JsonResponse({
            'success': True,
            'prompt': {
                'id': prompt.id,
                'category_id': prompt.category_id,
                'title': prompt.title,
                'prompt_text': prompt.prompt_text,
                'prompt_en': prompt.prompt_en,
                'order': prompt.order,
            }
        })

    except Exception as e:
        logger.error(f"Error creating video prompt: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@staff_member_required
@csrf_exempt
@require_http_methods(["POST"])
def update_video_prompt(request, prompt_id):
    """Update a video prompt"""
    try:
        prompt = VideoPrompt.objects.get(id=prompt_id)

        if 'title' in request.POST:
            prompt.title = request.POST['title']
        if 'prompt_text' in request.POST:
            prompt.prompt_text = request.POST['prompt_text']
        if 'prompt_en' in request.POST:
            prompt.prompt_en = request.POST['prompt_en']
        if 'order' in request.POST:
            prompt.order = int(request.POST['order'])
        if 'is_active' in request.POST:
            prompt.is_active = _b(request.POST['is_active'], prompt.is_active)
        if 'category_id' in request.POST:
            prompt.category_id = request.POST['category_id']
        if 'subcategory_id' in request.POST:
            sid = request.POST.get('subcategory_id')
            if sid in (None, "", "0"):
                prompt.subcategory = None
            else:
                sc = VideoPromptSubcategory.objects.get(pk=int(sid))
                if prompt.category_id and sc.category_id != int(prompt.category_id):
                    return JsonResponse({'error': 'subcategory does not belong to prompt category'}, status=400)
                prompt.subcategory = sc

        prompt.save()

        return JsonResponse({
            'success': True,
            'prompt': {
                'id': prompt.id,
                'category_id': prompt.category_id,
                'title': prompt.title,
                'prompt_text': prompt.prompt_text,
                'prompt_en': prompt.prompt_en,
                'order': prompt.order,
                'is_active': prompt.is_active,
            }
        })

    except VideoPromptSubcategory.DoesNotExist:
        return JsonResponse({'error': 'subcategory not found'}, status=404)
    except VideoPrompt.DoesNotExist:
        return JsonResponse({'error': 'Prompt not found'}, status=404)
    except Exception as e:
        logger.error(f"Error updating video prompt: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@staff_member_required
@csrf_exempt
@require_http_methods(["POST"])
def delete_video_prompt(request, prompt_id):
    """Delete a video prompt"""
    try:
        prompt = VideoPrompt.objects.get(id=prompt_id)
        prompt.delete()

        return JsonResponse({'success': True})

    except VideoPrompt.DoesNotExist:
        return JsonResponse({'error': 'Prompt not found'}, status=404)
    except Exception as e:
        logger.error(f"Error deleting video prompt: {e}")
        return JsonResponse({'error': str(e)}, status=500)


# ============================================================================
# Video Showcase API
# ============================================================================

@require_http_methods(["GET"])
def list_video_showcase(request):
    """List all video showcase examples - public endpoint"""
    mode = request.GET.get('mode', 't2v')  # i2v or t2v
    category = request.GET.get('category', 'all')

    videos = ShowcaseVideo.objects.filter(
        is_active=True,
        mode=mode
    ).order_by('order', '-created_at')

    if category and category != 'all':
        videos = videos.filter(category__slug=category)

    data = [{
        'id': video.id,
        'title': video.title,
        'prompt': video.prompt,
        'video_url': video.video_url,
        'thumbnail_url': video.thumbnail.url if video.thumbnail else None,
        'category': video.category.slug if video.category else None,
        'mode': video.mode,
        'order': video.order,
    } for video in videos]

    return JsonResponse({'examples': data})


@staff_member_required
@csrf_exempt
@require_http_methods(["POST"])
def create_video_showcase(request):
    """Create a new video showcase example"""
    try:
        title = request.POST.get('title')
        prompt = request.POST.get('prompt')
        category_id = request.POST.get('category_id')
        order = int(request.POST.get('order', 0))
        video_file = request.FILES.get('video_file')
        mode = (request.POST.get('mode') or 't2v').strip().lower()
        if mode not in {'i2v', 't2v'}:
            mode = 't2v'

        if not title or not prompt or not video_file:
            return JsonResponse({'error': 'Заполните название, промпт и выберите MP4 файл'}, status=400)

        ctype = (getattr(video_file, "content_type", "") or "").lower()
        if "mp4" not in ctype and not (getattr(video_file, "name", "").lower().endswith(".mp4")):
            return JsonResponse({'error': 'Поддерживается только MP4'}, status=400)

        try:
            optimized_url = _save_optimized_mp4(video_file, subdir="showcase_videos")
        except Exception as e:
            # fallback: save original file
            dst_dir = f"showcase_videos/{timezone.now():%Y/%m}/"
            storage_name = default_storage.generate_filename(dst_dir + (getattr(video_file, "name", "video.mp4")))
            storage_name = default_storage.save(storage_name, video_file)
            optimized_url = default_storage.url(storage_name)

        video = ShowcaseVideo.objects.create(
            title=title,
            prompt=prompt,
            video_url=optimized_url,
            mode=mode,
            category_id=category_id if category_id else None,
            order=order,
            uploaded_by=request.user,
            is_active=True
        )


        return JsonResponse({
            'success': True,
            'video': {
                'id': video.id,
                'title': video.title,
                'prompt': video.prompt,
                'video_url': video.video_url,
                'thumbnail_url': video.thumbnail.url if video.thumbnail else None,
                'order': video.order,
            }
        })

    except Exception as e:
        logger.error(f"Error creating video showcase: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@staff_member_required
@csrf_exempt
@require_http_methods(["POST"])
def update_video_showcase(request, video_id):
    """Update a video showcase example"""
    try:
        video = ShowcaseVideo.objects.get(id=video_id)

        if 'title' in request.POST:
            video.title = request.POST['title']
        if 'prompt' in request.POST:
            video.prompt = request.POST['prompt']
        if 'video_file' in request.FILES:
            video.video_url = _save_optimized_mp4(request.FILES['video_file'], subdir="showcase_videos")
        elif 'video_url' in request.POST:
            video.video_url = request.POST['video_url']
        if 'category_id' in request.POST:
            video.category_id = request.POST['category_id'] if request.POST['category_id'] else None
        if 'order' in request.POST:
            video.order = int(request.POST['order'])
        if 'mode' in request.POST:
            m = (request.POST['mode'] or '').strip().lower()
            if m in {'i2v', 't2v'}:
                video.mode = m
        if 'thumbnail' in request.FILES:
            video.thumbnail = request.FILES['thumbnail']

        video.save()

        return JsonResponse({
            'success': True,
            'video': {
                'id': video.id,
                'title': video.title,
                'prompt': video.prompt,
                'video_url': video.video_url,
                'thumbnail_url': video.thumbnail.url if video.thumbnail else None,
                'order': video.order,
            }
        })

    except ShowcaseVideo.DoesNotExist:
        return JsonResponse({'error': 'Video not found'}, status=404)
    except Exception as e:
        logger.error(f"Error updating video showcase: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@staff_member_required
@csrf_exempt
@require_http_methods(["POST"])
def delete_video_showcase(request, video_id):
    """Delete a video showcase example"""
    try:
        video = ShowcaseVideo.objects.get(id=video_id)
        video.delete()

        return JsonResponse({'success': True})

    except ShowcaseVideo.DoesNotExist:
        return JsonResponse({'error': 'Video not found'}, status=404)
    except Exception as e:
        logger.error(f"Error deleting video showcase: {e}")
        return JsonResponse({'error': str(e)}, status=500)
