# pages/views.py
from django.shortcuts import render
from django.views.generic import TemplateView
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q, Exists, OuterRef
import json


def age_accept(request):
    resp = JsonResponse({"ok": True})
    # ставим куку на 365 дней
    resp.set_cookie("age_ok", "1", max_age=60*60*24*365,
                    samesite="Lax", secure=False, path="/")
    return resp


def _ensure_session_key(request):
    """Обеспечиваем наличие session_key для гостевых лайков."""
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key


def home(request):
    # Получаем трендовые фото/видео для главной страницы (с учётом скрытых работ)
    trending_photos = get_trending_photos(request)
    trending_videos = get_trending_videos(request)

    # Смешиваем фото и видео в единую ленту (интерлив), максимум 12 карточек
    def _mix_lists(a, b, limit=12):
        out = []
        i = j = 0
        while len(out) < limit and (i < len(a) or j < len(b)):
            if i < len(a):
                out.append({"kind": "photo", "obj": a[i]})
                i += 1
                if len(out) >= limit:
                    break
            if j < len(b):
                out.append({"kind": "video", "obj": b[j]})
                j += 1
        return out

    trending_items = _mix_lists(trending_photos or [], trending_videos or [], 12)

    # Определяем лайкнутые id для текущего пользователя/гостя
    liked_photo_ids: set[int] = set()
    photo_ids = [p.id for p in trending_photos] if trending_photos else []

    if photo_ids:
        try:
            from gallery.models import PhotoLike
            if request.user.is_authenticated:
                liked_photo_ids = set(
                    PhotoLike.objects.filter(
                        user=request.user, photo_id__in=photo_ids
                    ).values_list("photo_id", flat=True)
                )
            else:
                skey = _ensure_session_key(request)
                liked_photo_ids = set(
                    PhotoLike.objects.filter(
                        user__isnull=True, session_key=skey, photo_id__in=photo_ids
                    ).values_list("photo_id", flat=True)
                )
        except ImportError:
            pass

    # Подготовим лайки видео для текущего пользователя/гостя
    liked_video_ids: set[int] = set()
    video_ids = [v.id for v in (trending_videos or [])]
    if video_ids:
        try:
            from gallery.models import VideoLike
            if request.user.is_authenticated:
                liked_video_ids = set(
                    VideoLike.objects.filter(
                        user=request.user, video_id__in=video_ids
                    ).values_list("video_id", flat=True)
                )
            else:
                skey = _ensure_session_key(request)
                liked_video_ids = set(
                    VideoLike.objects.filter(
                        user__isnull=True, session_key=skey, video_id__in=video_ids
                    ).values_list("video_id", flat=True)
                )
        except ImportError:
            pass

    # Инлайн-данные для слайдеров (мгновенный рендер без ожидания fetch)
    video_json = "[]"
    image_json = "[]"

    # Видео-примеры
    try:
        from gallery.models_slider_video import VideoSliderExample  # noqa
        videos = (
            VideoSliderExample.objects
            .filter(is_active=True)
            .filter(Q(video_file__isnull=False) | Q(video_url__gt=""))
            .order_by("order", "json_id")
        )
        vlist = []
        for v in videos:
            # Постер
            thumb_url = ""
            try:
                if v.thumbnail and getattr(v.thumbnail, "url", None):
                    thumb_url = v.thumbnail.url
            except Exception:
                thumb_url = ""
            vlist.append({
                "id": v.json_id,
                "title": v.title,
                "prompt": v.prompt,
                "video": v.video_src,
                "thumbnail": thumb_url,
                "description": v.description,
                "settings": {
                    "steps": int(getattr(v, "steps", 28) or 28),
                    "cfg": float(getattr(v, "cfg", 7.0) or 7.0),
                    "ratio": getattr(v, "ratio", "3:2"),
                    "seed": (v.seed if getattr(v, "seed", "auto") else "auto"),
                },
                "order": int(getattr(v, "order", 0) or 0),
            })
        video_json = json.dumps(vlist, ensure_ascii=False)
    except Exception:
        pass

    # Фото-примеры
    try:
        from gallery.models_slider import SliderExample  # noqa
        photos = (
            SliderExample.objects
            .filter(is_active=True, image__isnull=False)
            .order_by("order", "json_id")
        )
        plist = []
        for p in photos:
            img_url = ""
            try:
                if p.image and getattr(p.image, "url", None):
                    img_url = p.image.url
            except Exception:
                img_url = ""
            alt_text = getattr(p, "alt", None) or (p.title or "")
            plist.append({
                "id": p.json_id,
                "title": p.title,
                "prompt": p.prompt,
                "image": img_url or "/static/img/default.png",
                "description": p.description,
                "alt": alt_text,
                "settings": {
                    "steps": int(getattr(p, "steps", 28) or 28),
                    "cfg": float(getattr(p, "cfg", 7.0) or 7.0),
                    "ratio": getattr(p, "ratio", "3:2"),
                    "seed": getattr(p, "seed", "auto") or "auto",
                },
                "order": int(getattr(p, "order", 0) or 0),
            })
        image_json = json.dumps(plist, ensure_ascii=False)
    except Exception:
        pass

    context = {
        'trending_items': trending_items,
        'trending_photos': trending_photos,
        'liked_photo_ids': liked_photo_ids,
        'liked_video_ids': liked_video_ids,
        'video_slider_examples_json': video_json,
        'image_slider_examples_json': image_json,
    }
    return render(request, "pages/home.html", context)


def get_trending_photos(request):

    try:
        from gallery.models import PublicPhoto

        # Получаем фото за последний месяц
        last_month = timezone.now() - timedelta(days=30)

        # Скрываем публикации, привязанные к скрытым задачам (для посетителей).
        from gallery.models import JobHide

        base_qs = (
            PublicPhoto.objects.filter(
                created_at__gte=last_month,
                is_active=True
            )
            .select_related('uploaded_by', 'category')
            .annotate(
                hidden_by_owner=Exists(
                    JobHide.objects.filter(
                        user=OuterRef('uploaded_by_id'),
                        job_id=OuterRef('source_job_id')
                    )
                )
            )
        )

        if request.user.is_authenticated:
            # Показываем собственнику его же скрытые публикации, остальным — скрытые не показываем
            base_qs = base_qs.filter(
                Q(hidden_by_owner=False) | Q(uploaded_by_id=request.user.id)
            )
        else:
            base_qs = base_qs.filter(hidden_by_owner=False)

        trending_by_likes = base_qs.order_by(
            '-likes_count', '-view_count')[:12]
        return list(trending_by_likes)

    except ImportError:
        # Если модель PublicPhoto не существует или приложение gallery не подключено
        return []
    except Exception as e:
        # Логируем ошибку, но не ломаем страницу
        print(f"Error getting trending photos: {e}")
        return []

def get_trending_videos(request):
    """
    Возвращает список PublicVideo за последний месяц, отсортированных по лайкам/просмотрам,
    с фильтрацией скрытых работ владельцев.
    """
    try:
        from gallery.models import PublicVideo, JobHide

        last_month = timezone.now() - timedelta(days=30)
        base_qs = (
            PublicVideo.objects.filter(
                created_at__gte=last_month,
                is_active=True
            )
            .select_related('uploaded_by', 'category')
            .annotate(
                hidden_by_owner=Exists(
                    JobHide.objects.filter(
                        user=OuterRef('uploaded_by_id'),
                        job_id=OuterRef('source_job_id')
                    )
                )
            )
        )
        if request.user.is_authenticated:
            base_qs = base_qs.filter(
                Q(hidden_by_owner=False) | Q(uploaded_by_id=request.user.id)
            )
        else:
            base_qs = base_qs.filter(hidden_by_owner=False)

        trending_by_likes = base_qs.order_by('-likes_count', '-view_count')[:12]
        return list(trending_by_likes)
    except ImportError:
        return []
    except Exception as e:
        print(f"Error getting trending videos: {e}")
        return []


class RobotsView(TemplateView):
    """
    Dynamic robots.txt view
    """
    template_name = "pages/robots.txt"
    content_type = "text/plain"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        request = self.request
        base_url = f"{request.scheme}://{request.get_host()}"

        # domain
        # base_url = "https://test.com"

        context.update({
            'base_url': base_url,
            'sitemap_url': f"{base_url}/sitemap.xml",
        })

        return context


def about(request):
    return render(request, "pages/about.html")


def contact(request):
    return render(request, "pages/contact.html")


def privacy(request):
    return render(request, "pages/privacy.html")
