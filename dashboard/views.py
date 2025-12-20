# FILE: dashboard/views.py
from __future__ import annotations

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Count
from django.http import Http404, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.text import slugify
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods

from .models import Wallet, Profile
from generate.models import GenerationJob
from gallery.models import PublicPhoto, PhotoLike, VideoLike, PhotoSave, VideoSave, JobSave

# --- Константы стоимости/прав ---
TOKEN_COST = int(getattr(settings, "TOKEN_COST_PER_GEN", 10))
FREE_FOR_STAFF = bool(getattr(settings, "FREE_FOR_STAFF", True))

# --- Тарифные планы (USD) ---
PLANS = {
    "pack_100":        {"tokens": 100,   "price_usd": 5,   "title": "100 TOK"},
    "pack_500":        {"tokens": 500,   "price_usd": 10,  "title": "500 TOK"},
    "pack_1000":       {"tokens": 1000,  "price_usd": 20,  "title": "1000 TOK"},
    "pack_2000":       {"tokens": 2000,  "price_usd": 35,  "title": "2000 TOK"},
    "pack_5000":       {"tokens": 5000,  "price_usd": 50,  "title": "5000 TOK"},
    "pack_unlimited":  {"tokens": None,  "price_usd": 150, "title": "Безлимит", "unlimited": True},
}


def _get_plan_or_404(plan_id: str):
    plan = PLANS.get(plan_id)
    if not plan:
        raise Http404("Неизвестный тариф")
    return plan


def _job_has_file(job: GenerationJob) -> bool:
    return bool(
        getattr(job, "result_image", None)
        and job.result_image.name
        and default_storage.exists(job.result_image.name)
    )


def _price_for_user(user) -> int:
    """0 для staff при FREE_FOR_STAFF, иначе TOKEN_COST."""
    if user and user.is_authenticated and (user.is_staff or user.is_superuser) and FREE_FOR_STAFF:
        return 0
    return TOKEN_COST


def _gens_left_for_wallet(user, wallet: Wallet, price: int) -> tuple[int, str]:
    """
    Возвращает (gens_left, infinity_str).
    Если price == 0 → gens_left не используется, а infinity_str = '∞'.
    """
    if price == 0:
        return 0, "∞"
    bal = int(wallet.balance or 0)
    return bal // max(1, price), ""


@login_required
def me(request: HttpRequest) -> HttpResponse:
    try:
        return redirect("profile_short", username=request.user.username)
    except Exception:
        return redirect("dashboard:index")

@login_required
def index(request: HttpRequest) -> HttpResponse:
    from .models import Follow
    from gallery.models import PublicPhoto, PublicVideo

    # Всегда показываем все обработки независимо от ?only=published
    only_published = False
    wallet, _ = Wallet.objects.get_or_create(user=request.user)
    price = _price_for_user(request.user)
    gens_left, inf = _gens_left_for_wallet(request.user, wallet, price)

    # Статистика подписок
    followers_count = Follow.objects.filter(following=request.user).count()
    following_count = Follow.objects.filter(follower=request.user).count()

    # Подсчет публикаций: все завершенные работы (как в my-jobs)
    posts_count = GenerationJob.objects.filter(
        user=request.user,
        status=GenerationJob.Status.DONE
    ).filter(persisted=True).count()

    # Последняя активность: 5 последних задач пользователя
    recent_jobs = []
    try:
        qs = (
            GenerationJob.objects
            .filter(user=request.user, persisted=True)
            .order_by('-created_at')
        )[:5]

        for j in qs:
            title = (j.prompt or "Без названия").strip()
            s = slugify(title or "image") or "image"
            # Ограничим длину заголовка на уровне представления
            short = title[:80]
            try:
                img_url = reverse("generate:job_image", args=[j.pk, s])
            except Exception:
                img_url = ""
            try:
                detail_url = reverse("generate:job_detail", args=[j.pk, s])
            except Exception:
                detail_url = ""
            status = (j.status or "").upper()
            if status == "DONE":
                status_label, status_kind = "Готово", "done"
            elif status == "FAILED":
                status_label, status_kind = "Ошибка", "fail"
            elif status == "QUEUED":
                status_label, status_kind = "В очереди", "queue"
            elif status == "RUNNING":
                status_label, status_kind = "Обработка", "run"
            else:
                status_label, status_kind = (status or "Неизв."), "unk"

            recent_jobs.append({
                "id": j.pk,
                "title": short,
                "created_at": j.created_at,
                "status_label": status_label,
                "status_kind": status_kind,
                "img_url": img_url,
                "detail_url": detail_url,
            })
    except Exception:
        recent_jobs = []

    ctx = {
        "wallet": wallet,
        "price": price,
        "gens_left": gens_left,
        "gems_infinity": inf,  # '∞' для staff
        "TOKENS_PRICE_PER_GEN": TOKEN_COST,
        "recent_jobs": recent_jobs,
        "follow_stats": {
            "followers": followers_count,
            "following": following_count,
            "posts": posts_count,
        },
    }
    return render(request, "dashboard/index.html", ctx)


@login_required
def my_jobs(request):
    """
    Мои обработки - ФОТО и ВИДЕО раздельно.
    - 15 карточек на страницу.
    - Для каждой завершённой задачи приклеиваем инфо о публикации в галерее
      (бейдж + лайки/комменты/просмотры) только если фото реально активно.
    - Совместимо с моделями, где связь в PublicPhoto называется source_job ИЛИ job.
    - Возвращаем jobs_cards=[{"obj": job, "pub": {...}|None, "is_published": bool}, ...]
    """
    # Всегда показываем все обработки вне зависимости от параметра ?only=published
    only_published = False
    wallet, _ = Wallet.objects.get_or_create(user=request.user)

    # Определяем имя связи для фильтрации
    rel_name = None
    pf_names = {f.name for f in PublicPhoto._meta.get_fields()}
    if "source_job" in pf_names:
        rel_name = "source_job"
    elif "job" in pf_names:
        rel_name = "job"

    # ФОТО: только изображения
    photos_qs = (
        GenerationJob.objects
        .filter(
            user=request.user,
            status__in=[GenerationJob.Status.DONE,
                        GenerationJob.Status.PENDING_MODERATION]
        )
        .exclude(generation_type='video')  # Исключаем видео!
        .filter(persisted=True)
        .order_by("-created_at")
    )

    # Если нужны только опубликованные - фильтруем на уровне БД
    if only_published and rel_name:
        published_job_ids = PublicPhoto.objects.filter(
            uploaded_by=request.user,
            is_active=True
        ).values_list(f"{rel_name}_id", flat=True)
        photos_qs = photos_qs.filter(id__in=list(published_job_ids))

    # Photos counter: exclude already published photos (moved to gallery)
    published_photo_job_ids = []
    published_photos_count = 0
    try:
        if rel_name:
            published_photo_job_ids = list(
                PublicPhoto.objects.filter(
                    uploaded_by=request.user, is_active=True)
                .values_list(f"{rel_name}_id", flat=True)
            )
            published_photos_count = len(set(published_photo_job_ids))
    except Exception:
        published_photo_job_ids = []
        published_photos_count = 0

    try:
        photos_total = photos_qs.exclude(
            id__in=published_photo_job_ids).count()
    except Exception:
        photos_total = photos_qs.count()

    # ВИДЕО: только видео (аналогично фото)
    from gallery.models import PublicVideo
    videos_qs = (
        GenerationJob.objects
        .filter(
            user=request.user,
            generation_type='video',
            status__in=[GenerationJob.Status.DONE,
                        GenerationJob.Status.PENDING_MODERATION]
        )
        .filter(persisted=True)
        .order_by("-created_at")
    )

    # Если нужны только опубликованные видео - фильтруем на уровне БД
    if only_published:
        published_video_ids = PublicVideo.objects.filter(
            uploaded_by=request.user, is_active=True).values_list("source_job_id", flat=True)
        videos_qs = videos_qs.filter(id__in=list(published_video_ids))

    # Получаем информацию о публикации (как для фото)
    # Videos counter: exclude already published videos (moved to gallery)
    published_video_job_ids = []
    published_videos_count = 0
    try:
        published_video_job_ids = list(
            PublicVideo.objects.filter(
                uploaded_by=request.user, is_active=True)
            .values_list("source_job_id", flat=True)
        )
        published_videos_count = len(set(published_video_job_ids))
    except Exception:
        published_video_job_ids = []
        published_videos_count = 0

    try:
        videos_total = videos_qs.exclude(
            id__in=published_video_job_ids).count()
    except Exception:
        videos_total = videos_qs.count()

    # Total published badge (photos + videos)
    published_total = int(published_photos_count) + int(published_videos_count)
    # Показываем все видео без ограничения
    video_jobs = list(videos_qs)
    pub_videos_by_job = {}
    if video_jobs:
        job_ids = [j.id for j in video_jobs]
        published = PublicVideo.objects.filter(source_job__in=job_ids).only(
            "id", "source_job_id", "view_count", "title", "is_active",
            "likes_count", "comments_count"
        )
        pub_videos_by_job = {p.source_job_id: p for p in published}

    # Формируем cards аналогично фото
    videos_cards = []
    for j in video_jobs:
        p = pub_videos_by_job.get(j.id)
        if p and p.is_active:
            # Опубликовано
            videos_cards.append({
                "obj": j,
                "is_published": True,
                "pub": {
                    "id": p.id,
                    "likes": int(getattr(p, "likes_count", 0) or 0),
                    "comments": int(getattr(p, "comments_count", 0) or 0),
                    "saves": int(getattr(p, "saves_count", 0) or 0),
                    "views": int(getattr(p, "view_count", 0) or 0),
                },
            })
        elif p and not p.is_active:
            # На модерации
            videos_cards.append({
                "obj": j,
                "is_published": False,
                "pub": None,
                "pending_moderation": True,
            })
        else:
            # Не опубликовано
            videos_cards.append({
                "obj": j,
                "is_published": False,
                "pub": None,
                "pending_moderation": False,
            })

    paginator = Paginator(photos_qs, 500)
    page_obj = paginator.get_page(request.GET.get("page") or 1)
    jobs = list(page_obj.object_list)

    pub_by_job_id = {}
    if jobs and rel_name:
        job_ids = [j.id for j in jobs]

        # Ищем PublicPhoto как активные (опубликованные), так и неактивные (на модерации)
        filter_kwargs = {f"{rel_name}__in": job_ids}

        published = (
            PublicPhoto.objects
            .filter(**filter_kwargs)
            .only("id", rel_name, "view_count", "title", "image", "is_active",
                  "likes_count", "comments_count")
        )

        # key_attr == "source_job_id" или "job_id"
        key_attr = f"{rel_name}_id"
        pub_by_job_id = {getattr(p, key_attr): p for p in published}

    # Добавляем в карточки job-метрики (лайки/комменты) для всех работ
    from gallery.models import Like, JobComment

    cards = []
    for j in jobs:
        p = pub_by_job_id.get(j.id)

        # job-level metrics (для всех работ, включая неопубликованные)
        try:
            job_like_count = Like.objects.filter(job=j).count()
        except Exception:
            job_like_count = 0
        try:
            job_comment_count = JobComment.objects.filter(
                job=j, is_visible=True).count()
        except Exception:
            job_comment_count = 0
        try:
            job_save_count = JobSave.objects.filter(job=j).count()
        except Exception:
            job_save_count = 0
        try:
            job_liked = Like.objects.filter(user=request.user, job=j).exists()
        except Exception:
            job_liked = False

        if p and p.is_active:
            # Опубликовано в галерее
            cards.append({
                "obj": j,
                "is_published": True,
                "pub": {
                    "id": p.id,
                    "likes": int(getattr(p, "likes_count", 0) or 0),
                    "comments": int(getattr(p, "comments_count", 0) or 0),
                    "saves": int(getattr(p, "saves_count", 0) or 0),
                    "views": int(getattr(p, "view_count", 0) or 0),
                    "image_url": getattr(p.image, "url", None),
                    "detail_url_name": "gallery:photo_detail",
                },
                # job-level metrics (для отображения «как в галерее» на не/опубликованных)
                "job_like_count": job_like_count,
                "job_comment_count": job_comment_count,
                "job_liked": job_liked,
                "job_save_count": job_save_count,
            })
        elif p and not p.is_active:
            # На модерации
            cards.append({
                "obj": j,
                "is_published": False,
                "pub": None,
                "pending_moderation": True,
                "job_like_count": job_like_count,
                "job_comment_count": job_comment_count,
                "job_liked": job_liked,
                "job_save_count": job_save_count,
            })
        else:
            # Не отправлено на публикацию
            cards.append({
                "obj": j,
                "is_published": False,
                "pub": None,
                "pending_moderation": False,
                "job_like_count": job_like_count,
                "job_comment_count": job_comment_count,
                "job_liked": job_liked,
                "job_save_count": job_save_count,
            })

    # Liked sets for current viewer (initial like state on my-jobs grid)
    liked_photo_ids = set()
    liked_video_ids = set()
    try:
        # photo_pub_ids via pub_by_job_id map (active only)
        photo_pub_ids = [p.id for p in pub_by_job_id.values()
                         if getattr(p, "is_active", False)]
        if photo_pub_ids:
            if request.user.is_authenticated:
                liked_photo_ids = set(
                    PhotoLike.objects.filter(
                        user=request.user, photo_id__in=photo_pub_ids
                    ).values_list("photo_id", flat=True)
                )
            else:
                if not request.session.session_key:
                    request.session.save()
                skey = request.session.session_key
                liked_photo_ids = set(
                    PhotoLike.objects.filter(
                        user__isnull=True, session_key=skey, photo_id__in=photo_pub_ids
                    ).values_list("photo_id", flat=True)
                )
    except Exception:
        liked_photo_ids = set()

    # Saved photos initial state on page (published)
    saved_photo_ids = set()
    try:
        if request.user.is_authenticated:
            photo_pub_ids2 = [
                p.id for p in pub_by_job_id.values() if getattr(p, "is_active", False)]
            if photo_pub_ids2:
                saved_photo_ids = set(
                    PhotoSave.objects.filter(
                        user=request.user, photo_id__in=photo_pub_ids2
                    ).values_list("photo_id", flat=True)
                )
    except Exception:
        saved_photo_ids = set()

    try:
        # video_pub_ids via pub_videos_by_job map (active only)
        video_pub_ids = [p.id for p in pub_videos_by_job.values(
        ) if getattr(p, "is_active", False)]
        if video_pub_ids:
            if request.user.is_authenticated:
                liked_video_ids = set(
                    VideoLike.objects.filter(
                        user=request.user, video_id__in=video_pub_ids
                    ).values_list("video_id", flat=True)
                )
            else:
                if not request.session.session_key:
                    request.session.save()
                skey = request.session.session_key
                liked_video_ids = set(
                    VideoLike.objects.filter(
                        user__isnull=True, session_key=skey, video_id__in=video_pub_ids
                    ).values_list("video_id", flat=True)
                )
    except Exception:
        liked_video_ids = set()

    # Saved videos initial state on page (published)
    saved_video_ids = set()
    try:
        if request.user.is_authenticated:
            video_pub_ids2 = [
                p.id for p in pub_videos_by_job.values() if getattr(p, "is_active", False)]
            if video_pub_ids2:
                saved_video_ids = set(
                    VideoSave.objects.filter(
                        user=request.user, video_id__in=video_pub_ids2
                    ).values_list("video_id", flat=True)
                )
    except Exception:
        saved_video_ids = set()

    # Compute job-level likes and comments for ALL jobs (photos tab)
    liked_job_ids = set()
    job_like_counts = {}
    job_comment_counts = {}
    # Saves
    saved_job_ids = set()
    job_save_counts = {}

    try:
        job_ids_list = [j.id for j in jobs] if jobs else []
        if job_ids_list:
            from gallery.models import Like, JobComment
            # liked state for current user
            liked_job_ids = set(
                Like.objects.filter(user=request.user, job_id__in=job_ids_list)
                .values_list("job_id", flat=True)
            )
            # like counts
            for row in Like.objects.filter(job_id__in=job_ids_list).values("job_id").annotate(c=Count("id")):
                job_like_counts[row["job_id"]] = int(row["c"] or 0)
            # comments counts (root + replies)
            for row in JobComment.objects.filter(job_id__in=job_ids_list, is_visible=True).values("job_id").annotate(c=Count("id")):
                job_comment_counts[row["job_id"]] = int(row["c"] or 0)
            # save counts + initial saved set
            for row in JobSave.objects.filter(job_id__in=job_ids_list).values("job_id").annotate(c=Count("id")):
                job_save_counts[row["job_id"]] = int(row["c"] or 0)
            if request.user.is_authenticated:
                saved_job_ids = set(
                    JobSave.objects.filter(
                        user=request.user, job_id__in=job_ids_list)
                    .values_list("job_id", flat=True)
                )
    except Exception:
        liked_job_ids = set()
        job_like_counts = {}
        job_comment_counts = {}

    # Compute job-level likes/comments for video tab
    video_job_like_counts = {}
    video_job_comment_counts = {}
    video_job_save_counts = {}
    video_saved_job_ids = set()
    try:
        video_job_ids_list = [j.id for j in video_jobs] if video_jobs else []
        if video_job_ids_list:
            from gallery.models import Like, JobComment
            for row in Like.objects.filter(job_id__in=video_job_ids_list).values("job_id").annotate(c=Count("id")):
                video_job_like_counts[row["job_id"]] = int(row["c"] or 0)
            for row in JobComment.objects.filter(job_id__in=video_job_ids_list, is_visible=True).values("job_id").annotate(c=Count("id")):
                video_job_comment_counts[row["job_id"]] = int(row["c"] or 0)
            # saves for videos list (same JobSave model)
            for row in JobSave.objects.filter(job_id__in=video_job_ids_list).values("job_id").annotate(c=Count("id")):
                video_job_save_counts[row["job_id"]] = int(row["c"] or 0)
            # user saved set
            if request.user.is_authenticated:
                video_saved_job_ids = set(
                    JobSave.objects.filter(
                        user=request.user, job_id__in=video_job_ids_list)
                    .values_list("job_id", flat=True)
                )
    except Exception:
        video_job_like_counts = {}
        video_job_comment_counts = {}

    # Hidden ids (owned by current user) for UI toggle on My Jobs
    try:
        from gallery.models import JobHide
        owner_hidden_ids = set(
            JobHide.objects.filter(user=request.user).values_list(
                "job_id", flat=True)
        )
    except Exception:
        owner_hidden_ids = set()

    # Current user's profile privacy (for my-jobs page logic)
    try:
        my_prof = Profile.objects.filter(
            user=request.user).only("is_private").first()
        my_profile_is_private = bool(getattr(my_prof, "is_private", False))
    except Exception:
        my_profile_is_private = False

    return render(
        request,
        "gallery/my_jobs.html",
        {
            "jobs_cards": cards,
            "videos_cards": videos_cards,  # Используем videos_cards!
            "photos_total": photos_total,
            "videos_total": videos_total,
            "published_total": published_total,
            "can_manage_jobs": True,  # на /dashboard/my-jobs кнопки доступны
            "my_profile_is_private": my_profile_is_private,
            "wallet": wallet,
            "page_obj": page_obj,
            "paginator": paginator,
            "keep_query": "",
            "liked_photo_ids": liked_photo_ids,
            "liked_video_ids": liked_video_ids,
            "saved_photo_ids": saved_photo_ids,
            "saved_video_ids": saved_video_ids,
            "liked_job_ids": liked_job_ids,
            "job_like_counts": job_like_counts,
            "job_comment_counts": job_comment_counts,
            "job_save_counts": job_save_counts,
            "saved_job_ids": saved_job_ids,
            "video_job_like_counts": video_job_like_counts,
            "video_job_comment_counts": video_job_comment_counts,
            "video_job_save_counts": video_job_save_counts,
            "video_saved_job_ids": video_saved_job_ids,
            "hidden_job_ids": owner_hidden_ids,
            "show_only_published": False,
        },
    )


@login_required
def saved(request: HttpRequest) -> HttpResponse:
    """
    «Сохранённое» — закладки пользователя:
    - Фото (PublicPhoto через PhotoSave)
    - Видео (PublicVideo через VideoSave)
    - Работы (GenerationJob через JobSave) — включая неопубликованные
      Показываем работы в двух вкладках:
        • фото-вкладка: все image-работы (не video)
        • видео-вкладка: все video-работы
    """
    # Local imports for job-level interactions
    from gallery.models import Like, JobComment

    # Query saved sets
    photo_saves = (
        PhotoSave.objects.filter(user=request.user)
        .select_related("photo", "photo__uploaded_by")
        .order_by("-id")
    )
    video_saves = (
        VideoSave.objects.filter(user=request.user)
        .select_related("video", "video__uploaded_by")
        .order_by("-id")
    )
    job_saves = (
        JobSave.objects.filter(user=request.user)
        .select_related("job")
        .order_by("-id")
    )

    # Split saved jobs by type
    job_photo_saves = job_saves.exclude(job__generation_type="video")
    job_video_saves = job_saves.filter(job__generation_type="video")

    photo_ids = list(photo_saves.values_list("photo_id", flat=True))
    video_ids = list(video_saves.values_list("video_id", flat=True))
    job_ids = list(job_saves.values_list("job_id", flat=True))

    # Liked sets for initial UI state
    liked_photo_ids = set()
    liked_video_ids = set()
    liked_job_ids = set()
    if photo_ids:
        liked_photo_ids = set(
            PhotoLike.objects.filter(
                user=request.user, photo_id__in=photo_ids).values_list("photo_id", flat=True)
        )
    if video_ids:
        liked_video_ids = set(
            VideoLike.objects.filter(
                user=request.user, video_id__in=video_ids).values_list("video_id", flat=True)
        )
    if job_ids:
        liked_job_ids = set(
            Like.objects.filter(user=request.user, job_id__in=job_ids).values_list(
                "job_id", flat=True)
        )

    # Job metrics (likes/comments/saves) for saved jobs
    job_like_counts: dict[int, int] = {}
    job_comment_counts: dict[int, int] = {}
    job_save_counts: dict[int, int] = {}
    if job_ids:
        for row in Like.objects.filter(job_id__in=job_ids).values("job_id").annotate(c=Count("id")):
            job_like_counts[row["job_id"]] = int(row["c"] or 0)
        for row in JobComment.objects.filter(job_id__in=job_ids, is_visible=True).values("job_id").annotate(c=Count("id")):
            job_comment_counts[row["job_id"]] = int(row["c"] or 0)
        for row in JobSave.objects.filter(job_id__in=job_ids).values("job_id").annotate(c=Count("id")):
            job_save_counts[row["job_id"]] = int(row["c"] or 0)

    # Totals for tabs
    photo_total = photo_saves.count() + job_photo_saves.count()
    video_total = video_saves.count() + job_video_saves.count()

    # Save counts for public photos/videos (for bookmark counters on cards)
    photo_save_counts: dict[int, int] = {}
    video_save_counts: dict[int, int] = {}
    if photo_ids:
        for row in PhotoSave.objects.filter(photo_id__in=photo_ids).values("photo_id").annotate(c=Count("id")):
            photo_save_counts[int(row["photo_id"])] = int(row["c"] or 0)
    if video_ids:
        for row in VideoSave.objects.filter(video_id__in=video_ids).values("video_id").annotate(c=Count("id")):
            video_save_counts[int(row["video_id"])] = int(row["c"] or 0)

    # sets for saved-state toggles on this page
    saved_photo_ids = set(photo_ids or [])
    saved_video_ids = set(video_ids or [])

    ctx = {
        "photo_saves": photo_saves,
        "video_saves": video_saves,
        # merged per-tab job saves
        "job_photo_saves": job_photo_saves,
        "job_video_saves": job_video_saves,
        # counts for tabs
        "photo_total": photo_total,
        "video_total": video_total,
        # like/save state
        "liked_photo_ids": liked_photo_ids,
        "liked_video_ids": liked_video_ids,
        "liked_job_ids": liked_job_ids,
        "job_like_counts": job_like_counts,
        "job_comment_counts": job_comment_counts,
        "job_save_counts": job_save_counts,
        # public save counters
        "photo_save_counts": photo_save_counts,
        "video_save_counts": video_save_counts,
        # saved-state sets (all here are saved, but needed for aria-pressed/UI)
        "saved_photo_ids": saved_photo_ids,
        "saved_video_ids": saved_video_ids,
    }
    return render(request, "gallery/saved.html", ctx)


@login_required
def tips(request: HttpRequest) -> HttpResponse:
    return render(request, "dashboard/tips.html")


@login_required
def notifications_page(request: HttpRequest) -> HttpResponse:
    """
    Страница «Уведомления».
    Рендерим HTML, данные подгружаются через /dashboard/api/notifications/*.
    """
    return render(request, "dashboard/notifications.html")


def publication_deleted(request: HttpRequest) -> HttpResponse:
    """
    Страница «Публикация удалена».
    Показывается когда пользователь переходит по ссылке на удалённую публикацию.
    """
    return render(request, "dashboard/publication_deleted.html")


@login_required
def balance(request: HttpRequest) -> HttpResponse:
    wallet, _ = Wallet.objects.get_or_create(user=request.user)
    price = _price_for_user(request.user)
    gens_left, inf = _gens_left_for_wallet(request.user, wallet, price)
    ctx = {
        "wallet": wallet,
        "price": price,
        "gens_left": gens_left,
        "gems_infinity": inf,
        "TOKENS_PRICE_PER_GEN": TOKEN_COST,
    }
    return render(request, "dashboard/balance.html", ctx)

# --- Тарифы и покупка ---


def tariffs(request: HttpRequest) -> HttpResponse:
    wallet = None
    price = _price_for_user(
        request.user) if request.user.is_authenticated else TOKEN_COST
    gens_left = 0
    inf = ""
    if request.user.is_authenticated:
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        gens_left, inf = _gens_left_for_wallet(request.user, wallet, price)

    plans = [{"id": k, **v} for k, v in PLANS.items()]
    plans.sort(key=lambda p: (p.get("unlimited", False),
               p["tokens"] if p["tokens"] is not None else 10**9))
    return render(
        request,
        "dashboard/tariffs.html",
        {
            "plans": plans,
            "wallet": wallet,
            "price": price,
            "gens_left": gens_left,
            "gems_infinity": inf,
            "TOKENS_PRICE_PER_GEN": TOKEN_COST,
        },
    )


def purchase_start(request: HttpRequest, plan_id: str):
    _get_plan_or_404(plan_id)
    checkout_url = reverse("dashboard:purchase_checkout", args=[plan_id])
    if not request.user.is_authenticated:
        messages.info(
            request, "Чтобы пополнить баланс, авторизуйтесь на нашем сайте.")
        return redirect(f"{reverse('account_login')}?next={checkout_url}")
    return redirect(checkout_url)


@login_required
def purchase_checkout(request: HttpRequest, plan_id: str):
    plan = _get_plan_or_404(plan_id)
    wallet, _ = Wallet.objects.get_or_create(user=request.user)
    price = _price_for_user(request.user)
    gens_left, inf = _gens_left_for_wallet(request.user, wallet, price)
    return render(
        request,
        "dashboard/purchase_checkout.html",
        {
            "plan_id": plan_id,
            "plan": plan,
            "wallet": wallet,
            "price": price,
            "gens_left": gens_left,
            "gems_infinity": inf,
            "TOKENS_PRICE_PER_GEN": TOKEN_COST,
        },
    )


@login_required
@require_http_methods(["POST"])
@csrf_protect
def purchase_pay(request: HttpRequest, plan_id: str):
    plan = _get_plan_or_404(plan_id)
    if not settings.DEBUG:
        messages.error(request, "Платёжная система временно недоступна.")
        return redirect("dashboard:purchase_checkout", plan_id=plan_id)

    with transaction.atomic():
        wallet = Wallet.objects.select_for_update(
        ).get_or_create(user=request.user)[0]

        if plan.get("unlimited"):
            # Заглушка для безлимита
            wallet.balance = 10_000_000
            wallet.save(update_fields=["balance"])
            try:
                from .models import Notification
                Notification.create(
                    recipient=request.user,
                    actor=None,
                    type=Notification.Type.WALLET_TOPUP,
                    message="Безлимит активирован",
                    link=reverse("dashboard:balance"),
                    payload={"amount": "unlimited"},
                )
            except Exception:
                pass
            messages.success(request, "Безлимит активирован (заглушка).")
        else:
            # Валидация суммы токенов
            tokens = int(plan["tokens"])
            if tokens <= 0 or tokens > 100_000_000:
                messages.error(request, "Некорректное количество токенов.")
                return redirect("dashboard:purchase_checkout", plan_id=plan_id)

            wallet.topup(tokens)
            try:
                from .models import Notification
                Notification.create(
                    recipient=request.user,
                    actor=None,
                    type=Notification.Type.WALLET_TOPUP,
                    message=f"Баланс пополнен: +{tokens} TOK",
                    link=reverse("dashboard:balance"),
                    payload={"amount": int(tokens)},
                )
            except Exception:
                pass
            messages.success(request, f"Зачислено {tokens} TOK (заглушка).")

    return redirect("dashboard:balance")


@login_required
@require_http_methods(["POST"])
@csrf_protect
def avatar_upload(request: HttpRequest) -> HttpResponse:
    """
    Загрузка/обновление аватара пользователя.
    При AJAX (fetch/XMLHttpRequest) возвращает JSON.
    При обычной отправке — редирект в кабинет с сообщением.
    """
    f = request.FILES.get("avatar")
    is_ajax = request.headers.get(
        "X-Requested-With") in ("XMLHttpRequest", "fetch")

    if not f:
        if is_ajax:
            return JsonResponse({"success": False, "message": "Файл не выбран"}, status=400)
        messages.error(request, "Файл не выбран")
        return redirect("dashboard:index")

    try:
        profile, _ = Profile.objects.get_or_create(user=request.user)
        profile.avatar = f
        profile.save(update_fields=["avatar", "updated_at"])
        if is_ajax:
            avatar_url = getattr(profile.avatar, "url", "")
            return JsonResponse({"success": True, "message": "Аватар обновлён", "avatar_url": avatar_url})
        messages.success(request, "Аватар обновлён")
    except Exception:
        if is_ajax:
            return JsonResponse({"success": False, "message": "Ошибка загрузки файла"}, status=500)
        messages.error(request, "Ошибка загрузки файла")

    return redirect("dashboard:index")


@login_required
def profile(request: HttpRequest, username: str) -> HttpResponse:
    """
    Профиль пользователя в стиле «инсты»:
    - карточка: аватар, имя, @username, counters (подписчики/подписки/публикации), Follow/Unfollow
    - ниже: сетка обработок пользователя (фото/видео), как на странице /dashboard/my-jobs
    """
    from django.contrib.auth import get_user_model
    from .models import Profile, Follow
    from gallery.models import PublicPhoto, PublicVideo

    User = get_user_model()
    target = User.objects.filter(username=username).first(
    ) or User.objects.filter(username__iexact=username).first()
    if not target:
        raise Http404("Пользователь не найден")

    is_self = request.user.is_authenticated and request.user.id == target.id
    target_profile = Profile.objects.filter(user=target).first()

    # counters
    followers = Follow.objects.filter(following=target).count()
    following = Follow.objects.filter(follower=target).count()

    # Подсчет публикаций: все завершенные работы (как в my-jobs)
    posts = GenerationJob.objects.filter(
        user=target,
        status=GenerationJob.Status.DONE
    ).filter(persisted=True).count()

    # is_following (для кнопки)
    is_following = False
    # Проверяем, подписан ли target на текущего пользователя (для кнопки "подписаться в ответ")
    target_follows_me = False
    if request.user.is_authenticated and not is_self:
        is_following = Follow.objects.filter(
            follower=request.user, following=target).exists()
        target_follows_me = Follow.objects.filter(
            follower=target, following=request.user).exists()

    # Определяем имя связи PublicPhoto -> job СНАЧАЛА
    rel_name = None
    pf_names = {f.name for f in PublicPhoto._meta.get_fields()}
    if "source_job" in pf_names:
        rel_name = "source_job"
    elif "job" in pf_names:
        rel_name = "job"

    # Сформируем карточки обработок (фото)
    # Если профиль приватный (is_private=True) - показываем только опубликованные
    # Если профиль открытый (is_private=False) - показываем ВСЕ завершенные работы
    # Если профиль не создан — по умолчанию профиль открытый (False)
    is_profile_private = bool(getattr(target_profile, "is_private", False))
    # Владельцу профиля показываем все завершенные работы; для посетителей уважаем is_private:
    # - открытый профиль (is_private=False): видны все завершенные работы
    # - закрытый профиль (is_private=True): видны только опубликованные в галерее
    if is_self:
        is_profile_private = False

    # Сколько элементов показывать в сетке (по умолчанию высокое число, чтобы покрыть «все публикации» без изменения UI)
    try:
        grid_limit = int(request.GET.get("limit") or "120")
    except Exception:
        grid_limit = 120
    grid_limit = max(12, min(grid_limit, 500))

    # Счётчики вкладок:
    # - Фото: количество НЕопубликованных фото-работ (DONE|PENDING_MODERATION), видимых текущему зрителю
    # - Видео: количество НЕопубликованных видео-работ (DONE|PENDING_MODERATION), видимых текущему зрителю
    # - Опубликованные: активные публикации (PublicPhoto + PublicVideo), скрытые (JobHide) исключаются для чужих
    hidden_ids = []
    if not is_self:
        try:
            from gallery.models import JobHide
            hidden_ids = list(JobHide.objects.filter(
                user=target).values_list("job_id", flat=True))
        except Exception:
            hidden_ids = []

    # Определяем имя связи для PublicPhoto (source_job или job) — уже вычислялось выше
    rel_name = None
    try:
        pf_names = {f.name for f in PublicPhoto._meta.get_fields()}
        if "source_job" in pf_names:
            rel_name = "source_job"
        elif "job" in pf_names:
            rel_name = "job"
    except Exception:
        rel_name = None

    # Published sets (apply hidden filter for visitors)
    pub_photo_qs = PublicPhoto.objects.filter(
        uploaded_by=target, is_active=True)
    pub_video_qs = PublicVideo.objects.filter(
        uploaded_by=target, is_active=True)
    if hidden_ids:
        try:
            pub_photo_qs = pub_photo_qs.exclude(source_job_id__in=hidden_ids)
            pub_video_qs = pub_video_qs.exclude(source_job_id__in=hidden_ids)
        except Exception:
            pass
    published_photo_job_ids = []
    if rel_name:
        try:
            published_photo_job_ids = list(pub_photo_qs.values_list(
                f"{rel_name}_id", flat=True).distinct())
        except Exception:
            published_photo_job_ids = []
    published_video_job_ids = list(pub_video_qs.values_list(
        "source_job_id", flat=True).distinct())
    published_total = int(len(set(published_photo_job_ids))) + \
        int(len(set(published_video_job_ids)))

    # Base job sets user can see
    photos_base_qs = (
        GenerationJob.objects
        .filter(
            user=target,
            status__in=[GenerationJob.Status.DONE,
                        GenerationJob.Status.PENDING_MODERATION],
        )
        .exclude(generation_type='video')
        .filter(persisted=True)
    )
    videos_base_qs = (
        GenerationJob.objects
        .filter(
            user=target,
            generation_type='video',
            status__in=[GenerationJob.Status.DONE,
                        GenerationJob.Status.PENDING_MODERATION],
        )
        .filter(persisted=True)
    )
    if hidden_ids:
        photos_base_qs = photos_base_qs.exclude(id__in=hidden_ids)
        videos_base_qs = videos_base_qs.exclude(id__in=hidden_ids)

    # Exclude published from photos/videos counters
    try:
        photos_total = photos_base_qs.exclude(
            id__in=published_photo_job_ids).count()
    except Exception:
        photos_total = photos_base_qs.count()
    try:
        videos_total = videos_base_qs.exclude(
            id__in=published_video_job_ids).count()
    except Exception:
        videos_total = videos_base_qs.count()

    # Header "Публикации" = фото (неопубл.) + видео (неопубл.) + опубликованные
    posts = int(photos_total) + int(videos_total) + int(published_total)

    if is_profile_private:
        # Только опубликованные
        if rel_name:
            try:
                from gallery.models import JobHide
                hidden_ids = list(JobHide.objects.filter(
                    user=target).values_list("job_id", flat=True))
            except Exception:
                hidden_ids = []
            qs_pub = PublicPhoto.objects.filter(
                uploaded_by=target, is_active=True)
            if hidden_ids:
                qs_pub = qs_pub.exclude(source_job_id__in=hidden_ids)
            published_photo_job_ids = list(
                qs_pub.values_list(f"{rel_name}_id", flat=True)
            )
        else:
            published_photo_job_ids = []

        photos_qs = (
            GenerationJob.objects
            .filter(
                id__in=published_photo_job_ids,
                user=target,
                status__in=[GenerationJob.Status.DONE,
                            GenerationJob.Status.PENDING_MODERATION]
            )
            .exclude(generation_type='video')
            .order_by("-created_at")
        )[:grid_limit]
    else:
        # ВСЕ завершенные работы
        photos_qs = (
            GenerationJob.objects
            .filter(
                user=target,
                status__in=[GenerationJob.Status.DONE,
                            GenerationJob.Status.PENDING_MODERATION],
            )
            .exclude(generation_type='video')
            .filter(persisted=True)
            .order_by("-created_at")
        )

        # Исключить скрытые фото для не-владельца (скрытые полностью не видны)
        if not is_self:
            try:
                from gallery.models import JobHide
                hidden_ids = list(JobHide.objects.filter(
                    user=target).values_list("job_id", flat=True))
                if hidden_ids:
                    photos_qs = photos_qs.exclude(id__in=hidden_ids)
            except Exception:
                pass

        # Применяем лимит ПОСЛЕ фильтрации скрытых
        photos_qs = photos_qs[:grid_limit]

    pub_by_job_id = {}
    if photos_qs and rel_name:
        job_ids = [j.id for j in photos_qs]
        filter_kwargs = {f"{rel_name}__in": job_ids}
        published = (
            PublicPhoto.objects
            .filter(**filter_kwargs)
            .only("id", rel_name, "view_count", "title", "image", "is_active",
                  "likes_count", "comments_count")
        )
        key_attr = f"{rel_name}_id"
        pub_by_job_id = {getattr(p, key_attr): p for p in published}

    # Job-level metrics for photos (to match my_jobs page)
    liked_job_ids = set()
    job_like_counts = {}
    job_comment_counts = {}
    try:
        photo_job_ids_list = [j.id for j in photos_qs] if photos_qs else []
        if photo_job_ids_list:
            from gallery.models import Like, JobComment
            liked_job_ids = set(
                Like.objects.filter(user=request.user,
                                    job_id__in=photo_job_ids_list)
                .values_list("job_id", flat=True)
            )
            for row in Like.objects.filter(job_id__in=photo_job_ids_list).values("job_id").annotate(c=Count("id")):
                job_like_counts[row["job_id"]] = int(row["c"] or 0)
            for row in JobComment.objects.filter(job_id__in=photo_job_ids_list, is_visible=True).values("job_id").annotate(c=Count("id")):
                job_comment_counts[row["job_id"]] = int(row["c"] or 0)
    except Exception:
        liked_job_ids = set()
        job_like_counts = {}
        job_comment_counts = {}

    jobs_cards = []
    for j in photos_qs:
        p = pub_by_job_id.get(j.id)
        if p and p.is_active:
            jobs_cards.append({
                "obj": j,
                "is_published": True,
                "pub": {
                    "id": p.id,
                    "likes": int(getattr(p, "likes_count", 0) or 0),
                    "comments": int(getattr(p, "comments_count", 0) or 0),
                    "saves": int(getattr(p, "saves_count", 0) or 0),
                    "views": int(getattr(p, "view_count", 0) or 0),
                },
                "job_like_count": job_like_counts.get(j.id, 0),
                "job_comment_count": job_comment_counts.get(j.id, 0),
                "job_liked": (j.id in liked_job_ids),
            })
        elif p and not p.is_active:
            jobs_cards.append({
                "obj": j,
                "is_published": False,
                "pub": None,
                "pending_moderation": True,
                "job_like_count": job_like_counts.get(j.id, 0),
                "job_comment_count": job_comment_counts.get(j.id, 0),
                "job_liked": (j.id in liked_job_ids),
            })
        else:
            jobs_cards.append({
                "obj": j,
                "is_published": False,
                "pub": None,
                "pending_moderation": False,
                "job_like_count": job_like_counts.get(j.id, 0),
                "job_comment_count": job_comment_counts.get(j.id, 0),
                "job_liked": (j.id in liked_job_ids),
            })

    # Видео карточки
    # Если профиль приватный (is_private=True) - показываем только опубликованные
    # Если профиль открытый (is_private=False) - показываем ВСЕ завершенные работы
    if is_profile_private:
        # Только опубликованные
        try:
            from gallery.models import JobHide
            hidden_ids = list(JobHide.objects.filter(
                user=target).values_list("job_id", flat=True))
        except Exception:
            hidden_ids = []
        v_qs_pub = PublicVideo.objects.filter(
            uploaded_by=target, is_active=True)
        if hidden_ids:
            v_qs_pub = v_qs_pub.exclude(source_job_id__in=hidden_ids)
        published_video_job_ids = list(
            v_qs_pub.values_list("source_job_id", flat=True)
        )

        videos_qs = (
            GenerationJob.objects
            .filter(
                id__in=published_video_job_ids,
                user=target,
                generation_type='video',
                status__in=[GenerationJob.Status.DONE,
                            GenerationJob.Status.PENDING_MODERATION]
            )
            .order_by("-created_at")
        )[:grid_limit]
    else:
        # ВСЕ завершенные работы
        videos_qs = (
            GenerationJob.objects
            .filter(
                user=target,
                generation_type='video',
                status__in=[GenerationJob.Status.DONE,
                            GenerationJob.Status.PENDING_MODERATION]
            )
            .filter(persisted=True)
            .order_by("-created_at")
        )

    # Исключить скрытые видео для не-владельца (скрытые полностью не видны)
    if not is_self:
        try:
            from gallery.models import JobHide
            hidden_ids = list(JobHide.objects.filter(
                user=target).values_list("job_id", flat=True))
            if hidden_ids:
                videos_qs = videos_qs.exclude(id__in=hidden_ids)
        except Exception:
            pass

    # Применяем лимит ПОСЛЕ фильтрации скрытых
    videos_qs = videos_qs[:grid_limit]

    pub_videos_by_job = {}
    if videos_qs:
        job_ids = [j.id for j in videos_qs]
        published_v = PublicVideo.objects.filter(source_job__in=job_ids).only(
            "id", "source_job_id", "view_count", "title", "is_active",
            "likes_count", "comments_count"
        )
        pub_videos_by_job = {p.source_job_id: p for p in published_v}

    from gallery.models import Like, JobComment

    videos_cards = []
    for j in videos_qs:
        p = pub_videos_by_job.get(j.id)

        # job-level metrics for ALL video jobs (published or not)
        try:
            v_job_like_count = Like.objects.filter(job=j).count()
        except Exception:
            v_job_like_count = 0
        try:
            v_job_comment_count = JobComment.objects.filter(
                job=j, is_visible=True).count()
        except Exception:
            v_job_comment_count = 0
        try:
            v_job_save_count = JobSave.objects.filter(job=j).count()
        except Exception:
            v_job_save_count = 0
        try:
            v_job_liked = Like.objects.filter(
                user=request.user, job=j).exists()
        except Exception:
            v_job_liked = False

        if p and p.is_active:
            videos_cards.append({
                "obj": j,
                "is_published": True,
                "pub": {
                    "id": p.id,
                    "likes": int(getattr(p, "likes_count", 0) or 0),
                    "comments": int(getattr(p, "comments_count", 0) or 0),
                    "saves": int(getattr(p, "saves_count", 0) or 0),
                    "views": int(getattr(p, "view_count", 0) or 0),
                },
                "job_like_count": v_job_like_count,
                "job_comment_count": v_job_comment_count,
                "job_liked": v_job_liked,
                "job_save_count": v_job_save_count,
            })
        elif p and not p.is_active:
            videos_cards.append({
                "obj": j,
                "is_published": False,
                "pub": None,
                "pending_moderation": True,
                "job_like_count": v_job_like_count,
                "job_comment_count": v_job_comment_count,
                "job_liked": v_job_liked,
                "job_save_count": v_job_save_count,
            })
        else:
            videos_cards.append({
                "obj": j,
                "is_published": False,
                "pub": None,
                "pending_moderation": False,
                "job_like_count": v_job_like_count,
                "job_comment_count": v_job_comment_count,
                "job_liked": v_job_liked,
                "job_save_count": v_job_save_count,
            })

    # Published lists for not owner (render PublicPhoto/PublicVideo directly with actions)
    pub_photos = []
    pub_videos = []
    if not is_self:
        try:
            from gallery.models import JobHide
            hidden_ids = list(JobHide.objects.filter(
                user=target).values_list("job_id", flat=True))
            pf_qs = PublicPhoto.objects.filter(uploaded_by=target, is_active=True).select_related('source_job').annotate(
                saves_count=Count("saves", distinct=True))
            if hidden_ids:
                pf_qs = pf_qs.exclude(source_job_id__in=hidden_ids)
            pub_photos = list(pf_qs.order_by("-created_at")[:grid_limit])
        except Exception:
            pub_photos = []
        try:
            from gallery.models import JobHide
            hidden_ids = list(JobHide.objects.filter(
                user=target).values_list("job_id", flat=True))
            pv_qs = PublicVideo.objects.filter(uploaded_by=target, is_active=True).select_related('source_job').annotate(
                saves_count=Count("saves", distinct=True))
            if hidden_ids:
                pv_qs = pv_qs.exclude(source_job_id__in=hidden_ids)
            pub_videos = list(pv_qs.order_by("-created_at")[:grid_limit])
        except Exception:
            pub_videos = []

    # Liked sets for current viewer (for initial like state on profile grid)
    liked_photo_ids = set()
    liked_video_ids = set()
    try:
        photo_pub_ids = ([p.id for p in pub_photos] if not is_self else [
                         p.id for p in pub_by_job_id.values() if getattr(p, "is_active", False)])
        if photo_pub_ids:
            if request.user.is_authenticated:
                liked_photo_ids = set(
                    PhotoLike.objects.filter(
                        user=request.user, photo_id__in=photo_pub_ids
                    ).values_list("photo_id", flat=True)
                )
            else:
                if not request.session.session_key:
                    request.session.save()
                skey = request.session.session_key
                liked_photo_ids = set(
                    PhotoLike.objects.filter(
                        user__isnull=True, session_key=skey, photo_id__in=photo_pub_ids
                    ).values_list("photo_id", flat=True)
                )
    except Exception:
        liked_photo_ids = set()

    try:
        video_pub_ids = ([p.id for p in pub_videos] if not is_self else [
                         p.id for p in pub_videos_by_job.values() if getattr(p, "is_active", False)])
        if video_pub_ids:
            if request.user.is_authenticated:
                liked_video_ids = set(
                    VideoLike.objects.filter(
                        user=request.user, video_id__in=video_pub_ids
                    ).values_list("video_id", flat=True)
                )
            else:
                if not request.session.session_key:
                    request.session.save()
                skey = request.session.session_key
                liked_video_ids = set(
                    VideoLike.objects.filter(
                        user__isnull=True, session_key=skey, video_id__in=video_pub_ids
                    ).values_list("video_id", flat=True)
                )
    except Exception:
        liked_video_ids = set()

    # Saved sets for current viewer (initial state)
    saved_photo_ids = set()
    saved_video_ids = set()
    try:
        if request.user.is_authenticated:
            # Photos: saved in published (active) items for the grid
            photo_pub_ids2 = ([p.id for p in pub_photos] if not is_self else [
                p.id for p in pub_by_job_id.values() if getattr(p, "is_active", False)
            ])
            if photo_pub_ids2:
                saved_photo_ids = set(
                    PhotoSave.objects.filter(
                        user=request.user, photo_id__in=photo_pub_ids2)
                    .values_list("photo_id", flat=True)
                )
    except Exception:
        saved_photo_ids = set()
    try:
        if request.user.is_authenticated:
            video_pub_ids2 = ([p.id for p in pub_videos] if not is_self else [
                p.id for p in pub_videos_by_job.values() if getattr(p, "is_active", False)
            ])
            if video_pub_ids2:
                saved_video_ids = set(
                    VideoSave.objects.filter(
                        user=request.user, video_id__in=video_pub_ids2)
                    .values_list("video_id", flat=True)
                )
    except Exception:
        saved_video_ids = set()

    # Рендерим «точь‑в‑точь my_jobs» под шапкой профиля, без возможности удаления/публикации
    # Hidden jobs set for owner (used to render toggle state)
    owner_hidden_ids = set()
    if is_self:
        try:
            from gallery.models import JobHide
            owner_hidden_ids = set(JobHide.objects.filter(
                user=target).values_list("job_id", flat=True))
        except Exception:
            owner_hidden_ids = set()

    # Safety net: ensure hidden jobs are removed from cards for non-owners, even if any branch above missed it
    if not is_self:
        try:
            from gallery.models import JobHide
            __hidden_ids = set(JobHide.objects.filter(
                user=target).values_list("job_id", flat=True))
        except Exception:
            __hidden_ids = set()
        if __hidden_ids:
            jobs_cards = [c for c in jobs_cards if getattr(
                c.get("obj"), "id", None) not in __hidden_ids]
            videos_cards = [c for c in videos_cards if getattr(
                c.get("obj"), "id", None) not in __hidden_ids]
            # keep counters consistent with what is actually rendered
            photos_total = len(jobs_cards)
            videos_total = len(videos_cards)
            posts = int(photos_total) + int(videos_total) + \
                int(published_total)

    return render(
        request,
        "gallery/my_jobs.html",
        {
            # Шапка профиля (вставляется сверху внутри my_jobs при profile_header=True)
            "profile_header": True,
            "target": target,
            "target_profile": target_profile,
            "followers": followers,
            "following": following,
            "posts": posts,
            "is_self": is_self,
            "is_following": is_following,
            "target_follows_me": target_follows_me,

            # Параметры my_jobs
            "jobs_cards": jobs_cards,
            "videos_cards": videos_cards,
            "photos_total": photos_total,
            "videos_total": videos_total,
            "published_total": published_total,
            "liked_photo_ids": liked_photo_ids,
            "liked_video_ids": liked_video_ids,
            "saved_photo_ids": saved_photo_ids,
            "saved_video_ids": saved_video_ids,
            "hidden_job_ids": owner_hidden_ids,

            # Управление доступом — скрываем «Удалить/Поделиться» для чужих профилей
            "can_manage_jobs": bool(is_self),

            # Пагинация для профиля не используется (полный блок), но шаблон ожидает ключи
            "wallet": None,
            "page_obj": None,
            "paginator": None,
            "keep_query": "",
            "pub_photos": pub_photos,
            "pub_videos": pub_videos,
            "show_only_published": is_profile_private,
        },
    )


@login_required
@require_http_methods(["POST"])
@csrf_protect
def toggle_profile_privacy(request: HttpRequest) -> HttpResponse:
    """
    Переключает приватность профиля (is_private).
    Возвращает JSON при AJAX-запросе; иначе делает редирект.
    """
    is_ajax = request.headers.get(
        "X-Requested-With") in ("XMLHttpRequest", "fetch")
    try:
        profile, _ = Profile.objects.get_or_create(user=request.user)
        profile.is_private = not profile.is_private
        profile.save(update_fields=["is_private", "updated_at"])

        status_text = "Приватный профиль" if profile.is_private else "Открытый профиль"
        if is_ajax:
            return JsonResponse({
                "success": True,
                "is_private": profile.is_private,
                "message": status_text
            })
        messages.success(request, status_text)
    except Exception:
        if is_ajax:
            return JsonResponse({"success": False, "message": "Ошибка"}, status=500)
        messages.error(request, "Ошибка при изменении настроек")
    return redirect("dashboard:index")


@login_required
@require_http_methods(["POST"])
@csrf_protect
def avatar_delete(request: HttpRequest) -> HttpResponse:
    """
    Удаление аватара пользователя.
    Возвращает JSON при AJAX-запросе; иначе делает редирект с сообщением.
    """
    # Подготовим целевой редирект заранее, чтобы иметь явный возврат в любой ветке
    is_ajax = request.headers.get(
        "X-Requested-With") in ("XMLHttpRequest", "fetch")
    next_url = request.META.get("HTTP_REFERER")
    try:
        fallback_profile = reverse("profile_short", args=[
                                   request.user.username])
    except Exception:
        fallback_profile = None
    try:
        profile, _ = Profile.objects.get_or_create(user=request.user)
        if getattr(profile, "avatar", None):
            # Сначала удалим файл из стораджа, затем почистим поле
            try:
                name = profile.avatar.name
            except Exception:
                name = None
            try:
                profile.avatar.delete(save=False)
            except Exception:
                pass
            if name:
                try:
                    default_storage.delete(name)
                except Exception:
                    pass
            profile.avatar = None
            profile.save(update_fields=["avatar", "updated_at"])
        if is_ajax:
            return JsonResponse({"success": True, "message": "Аватар удалён", "avatar_url": ""})
        messages.success(request, "Аватар удалён")
        # НЕ-AJAX успешный случай — немедленный редирект назад/в профиль
        return redirect(next_url or fallback_profile or reverse("dashboard:index"))
    except Exception:
        if is_ajax:
            return JsonResponse({"success": False, "message": "Ошибка при удалении аватара"}, status=500)
        messages.error(request, "Ошибка при удалении аватара")
        # НЕ-AJAX ошибка — тоже явный редирект
        return redirect(next_url or fallback_profile or reverse("dashboard:index"))

    # После не-AJAX запроса возвращаемся туда, откуда пришли (обычно профиль),
    # иначе — на страницу профиля текущего пользователя, а уже потом — в кабинет.
    next_url = request.META.get("HTTP_REFERER")
    try:
        fallback_profile = reverse("profile_short", args=[
                                   request.user.username])
    except Exception:
        fallback_profile = None
    return redirect(next_url or fallback_profile or reverse("dashboard:index"))
