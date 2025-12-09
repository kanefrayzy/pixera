"""
Views для управления API токенами и балансом
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.conf import settings
from decimal import Decimal

from .models_api import APIToken, APIBalance, APITransaction, APIUsageLog
from .models import Wallet, Follow, Profile
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count, Q
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
import re


@login_required
def api_dashboard(request):
    """Главная страница API управления"""
    # Получаем или создаем баланс
    balance, created = APIBalance.objects.get_or_create(user=request.user)

    # Получаем токены пользователя
    tokens = APIToken.objects.filter(user=request.user)

    # Получаем последние транзакции
    recent_transactions = APITransaction.objects.filter(user=request.user)[:10]

    # Статистика
    total_requests = sum(token.total_requests for token in tokens)
    total_generations = sum(token.total_generations for token in tokens)

    # Расчет стоимости одной генерации
    base_cost = Decimal(str(settings.TOKEN_COST_PER_GEN))  # Наша стоимость
    user_cost = base_cost * 2  # Цена для пользователя x2

    context = {
        'balance': balance,
        'tokens': tokens,
        'recent_transactions': recent_transactions,
        'total_requests': total_requests,
        'total_generations': total_generations,
        'base_cost': base_cost,
        'user_cost': user_cost,
        'cost_per_generation': user_cost,
    }

    # Очищаем токен из сессии после рендера (будет показан в модальном окне)
    if 'new_token' in request.session:
        # Сохраняем для рендера, но удалим после
        request.session.modified = True

    response = render(request, 'dashboard/api_dashboard.html', context)

    # Удаляем токен из сессии после рендера
    if 'new_token' in request.session:
        del request.session['new_token']

    return response


@login_required
@require_http_methods(["POST"])
def create_token(request):
    """Создание нового API токена"""
    name = request.POST.get('name', '').strip()

    if not name:
        messages.error(request, 'Укажите название токена')
        return redirect('dashboard:api:dashboard')

    # Ограничение на количество токенов
    if APIToken.objects.filter(user=request.user).count() >= 10:
        messages.error(request, 'Достигнут лимит токенов (максимум 10)')
        return redirect('dashboard:api:dashboard')

    # Создаем токен
    token = APIToken.objects.create(
        user=request.user,
        name=name,
        token=APIToken.generate_token()
    )

    # Сохраняем токен в сессии для показа в модальном окне
    request.session['new_token'] = {
        'name': token.name,
        'token': token.token
    }

    return redirect('dashboard:api:dashboard')


@login_required
@require_http_methods(["POST"])
def delete_token(request, token_id):
    """Удаление API токена"""
    token = get_object_or_404(APIToken, id=token_id, user=request.user)
    token_name = token.name
    token.delete()

    messages.success(request, f'Токен "{token_name}" удален')
    return redirect('dashboard:api:dashboard')


@login_required
@require_http_methods(["POST"])
def toggle_token(request, token_id):
    """Активация/деактивация токена"""
    token = get_object_or_404(APIToken, id=token_id, user=request.user)
    token.is_active = not token.is_active
    token.save()

    status = 'активирован' if token.is_active else 'деактивирован'
    messages.success(request, f'Токен "{token.name}" {status}')

    return redirect('dashboard:api:dashboard')


@login_required
def api_documentation(request):
    """Страница документации API"""
    # Расчет стоимости
    base_cost = Decimal(str(settings.TOKEN_COST_PER_GEN))
    user_cost = base_cost * 2

    # Получаем баланс
    balance, _ = APIBalance.objects.get_or_create(user=request.user)

    context = {
        'cost_per_generation': user_cost,
        'balance': balance,
    }

    return render(request, 'dashboard/api_documentation.html', context)


@login_required
def api_balance_page(request):
    """Страница управления балансом"""
    balance, _ = APIBalance.objects.get_or_create(user=request.user)
    transactions = APITransaction.objects.filter(user=request.user)[:50]

    context = {
        'balance': balance,
        'transactions': transactions,
    }

    return render(request, 'dashboard/api_balance.html', context)


@login_required
@require_http_methods(["POST"])
def deposit_balance(request):
    """Пополнение баланса (заглушка)"""
    try:
        amount = Decimal(request.POST.get('amount', '0'))

        if amount <= 0:
            messages.error(request, 'Сумма должна быть больше нуля')
            return redirect('dashboard:api_balance')

        if amount > 10000:
            messages.error(request, 'Максимальная сумма пополнения: $10,000')
            return redirect('dashboard:api_balance')

        # Получаем баланс
        balance, _ = APIBalance.objects.get_or_create(user=request.user)

        # Пополняем (пока заглушка, позже подключите платежную систему)
        balance.deposit(
            amount, description='Пополнение баланса (тестовый режим)')

        # Уведомление о пополнении API-баланса
        try:
            from .models import Notification
            from django.urls import reverse
            Notification.create(
                recipient=request.user,
                actor=None,
                type=Notification.Type.WALLET_TOPUP,
                message=f"API баланс пополнен: +${amount}",
                link=reverse("dashboard:api:balance"),
                payload={"amount_usd": float(amount)},
            )
        except Exception:
            pass

        messages.success(
            request,
            f'Баланс пополнен на ${amount}. Это тестовое пополнение, реальная оплата будет подключена позже.'
        )

    except (ValueError, TypeError):
        messages.error(request, 'Некорректная сумма')

    return redirect('dashboard:api_balance')


@login_required
def api_usage_stats(request):
    """Статистика использования API"""
    tokens = APIToken.objects.filter(user=request.user)

    # Собираем статистику по каждому токену
    token_stats = []
    for token in tokens:
        logs = APIUsageLog.objects.filter(token=token)
        recent_logs = logs[:20]

        token_stats.append({
            'token': token,
            'total_cost': sum(log.cost for log in logs),
            'recent_logs': recent_logs,
        })

    context = {
        'token_stats': token_stats,
    }

    return render(request, 'dashboard/api_usage_stats.html', context)


@login_required
@require_http_methods(["POST"])
def admin_topup(request):
    """
    STAFF-only: пополнение токенов по username.
    Формат запроса: username, amount, reason? (form-data or x-www-form-urlencoded)
    Ответ: JSON { ok: true, username, new_balance } или { ok: false, error }
    """
    if not request.user.is_staff:
        return JsonResponse({"ok": False, "error": "forbidden"}, status=403)

    username = (request.POST.get("username") or "").strip()
    reason = (request.POST.get("reason") or "").strip()
    try:
        amount = int(request.POST.get("amount") or "0")
    except Exception:
        amount = 0

    if not username or amount <= 0:
        return JsonResponse({"ok": False, "error": "invalid params"}, status=400)
    if amount > 100_000_000:
        return JsonResponse({"ok": False, "error": "amount too large"}, status=400)

    User = get_user_model()
    user = User.objects.filter(username=username).first(
    ) or User.objects.filter(username__iexact=username).first()
    if not user:
        return JsonResponse({"ok": False, "error": "user not found"}, status=404)

    with transaction.atomic():
        wallet, _ = Wallet.objects.select_for_update().get_or_create(user=user)
        wallet.topup(amount)

        # Здесь можно добавить запись в журнал транзакций/аудит, если потребуется:
        # AdminTopupLog.objects.create(admin=request.user, user=user, amount=amount, reason=reason)

        # Уведомление пользователю о пополнении администратором
        try:
            from .models import Notification
            from django.urls import reverse
            Notification.create(
                recipient=user,
                actor=request.user,
                type=Notification.Type.WALLET_TOPUP,
                message=f"Админ пополнил ваш баланс: +{amount} TOK",
                link=reverse("dashboard:balance"),
                payload={"amount": int(amount), "reason": reason},
            )
        except Exception:
            pass

    return JsonResponse({"ok": True, "username": user.username, "new_balance": int(wallet.balance)})

# API endpoint для проверки баланса (для использования в API)


@require_http_methods(["GET"])
def check_balance_api(request):
    """API endpoint для проверки баланса по токену"""
    auth_header = request.headers.get('Authorization', '')

    if not auth_header.startswith('Bearer '):
        return JsonResponse({'error': 'Invalid authorization header'}, status=401)

    token_value = auth_header[7:]  # Убираем 'Bearer '

    try:
        token = APIToken.objects.get(token=token_value, is_active=True)
        balance = APIBalance.objects.get(user=token.user)

        return JsonResponse({
            'balance': float(balance.balance),
            'total_spent': float(balance.total_spent),
            'total_requests': token.total_requests,
            'total_generations': token.total_generations,
        })
    except APIToken.DoesNotExist:
        return JsonResponse({'error': 'Invalid token'}, status=401)
    except APIBalance.DoesNotExist:
        return JsonResponse({'error': 'Balance not found'}, status=404)


@login_required
@require_http_methods(["GET"])
def wallet_info(request):
    """
    Текущий баланс кошелька авторизованного пользователя.
    Возвращает безопасный JSON для обновления дровера в реальном времени.
    """
    wallet = Wallet.objects.filter(user=request.user).first()
    bal = int(getattr(wallet, "balance", 0) or 0)
    try:
        price = int(getattr(settings, "TOKEN_COST_PER_GEN", 10))
    except Exception:
        price = 10
    gens_left = 0 if price <= 0 else (bal // max(1, price))
    return JsonResponse({"ok": True, "balance": bal, "gens_left": gens_left, "price": price})


@login_required
@require_http_methods(["POST"])
def follow_toggle(request):
    """
    Подписаться/отписаться на пользователя.
    In:
      - username (form-data) или JSON { "username": "..." }
    Out JSON:
      { ok: true, following: bool, followers_count: int }
    """
    username = (request.POST.get("username") or "").strip()
    if not username and request.content_type and "application/json" in request.content_type:
        try:
            import json
            payload = json.loads(request.body.decode("utf-8"))
            username = (payload.get("username") or "").strip()
        except Exception:
            pass

    if not username:
        return JsonResponse({"ok": False, "error": "username required"}, status=400)

    User = get_user_model()
    target = User.objects.filter(username=username).first(
    ) or User.objects.filter(username__iexact=username).first()
    if not target:
        return JsonResponse({"ok": False, "error": "user not found"}, status=404)
    if target.id == request.user.id:
        return JsonResponse({"ok": False, "error": "self follow not allowed"}, status=400)

    rel = Follow.objects.filter(
        follower=request.user, following=target).first()
    if rel:
        rel.delete()
        following = False
    else:
        Follow.objects.create(follower=request.user, following=target)
        following = True
        # Уведомление владельцу профиля о новой подписке
        try:
            from .models import Notification
            Notification.create(
                recipient=target,
                actor=request.user,
                type=Notification.Type.FOLLOW,
                message=f"@{request.user.username} подписался на вас",
                link=f"/dashboard/profile/{request.user.username}",
                payload={}
            )
        except Exception:
            pass

    followers_count = Follow.objects.filter(following=target).count()
    return JsonResponse({"ok": True, "following": following, "followers_count": followers_count})


@login_required
@require_http_methods(["GET"])
def follow_counters(request, username):
    """
    Возвращает счётчики подписок/подписчиков и публикаций для username.
    Out JSON:
      { ok: true, followers: int, following: int, posts: int }
    """
    User = get_user_model()
    target = User.objects.filter(username=username).first(
    ) or User.objects.filter(username__iexact=username).first()
    if not target:
        return JsonResponse({"ok": False, "error": "user not found"}, status=404)

    followers = Follow.objects.filter(following=target).count()
    following = Follow.objects.filter(follower=target).count()

    # Публикации = только сохранённые пользователем завершенные работы (как в my-jobs)
    try:
        from generate.models import GenerationJob
        posts = GenerationJob.objects.filter(
            user=target, status=GenerationJob.Status.DONE).filter(persisted=True).count()
    except Exception:
        posts = 0

    return JsonResponse({"ok": True, "followers": followers, "following": following, "posts": posts})


@login_required
@require_http_methods(["GET"])
def follow_search(request):
    """
    Поиск аккаунтов для подписки (инстаграм-логика).
    GET params:
      - q: строка поиска (username или first_name, частичное совпадение)
      - limit: int (опц., по умолч. 10)
    Возвращает:
      { ok: true, users: [{username, name, avatar_url, is_following, followers, following}] }
    """
    q = (request.GET.get("q") or "").strip()
    try:
        limit = int(request.GET.get("limit") or "10")
    except Exception:
        limit = 10
    limit = max(1, min(limit, 50))

    User = get_user_model()
    qs = User.objects.exclude(id=request.user.id)

    if q:
        qs = qs.filter(
            Q(username__icontains=q) |
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q)
        )

    # Аннотируем количеством подписчиков
    qs = qs.annotate(followers_count=Count("followers_relations", distinct=True)) \
           .order_by("-followers_count", "username")[:limit]

    # Предзагрузка профилей
    user_ids = [u.id for u in qs]
    profiles = {p.user_id: p for p in Profile.objects.filter(
        user_id__in=user_ids)}
    # Какие уже подписаны
    already = set(Follow.objects.filter(follower=request.user,
                  following_id__in=user_ids).values_list("following_id", flat=True))
    # Счётчики following
    following_counts = dict(
        Follow.objects.filter(follower_id__in=user_ids).values_list(
            "follower_id").annotate(c=Count("id"))
    )
    followers_counts = dict(
        Follow.objects.filter(following_id__in=user_ids).values_list(
            "following_id").annotate(c=Count("id"))
    )

    items = []
    for u in qs:
        prof = profiles.get(u.id)
        items.append({
            "username": u.username,
            "name": (u.first_name or "")[:64],
            "avatar_url": getattr(prof.avatar, "url", "") if prof and getattr(prof, "avatar", None) else "",
            "is_following": u.id in already,
            "followers": int(followers_counts.get(u.id, 0)),
            "following": int(following_counts.get(u.id, 0)),
        })

    return JsonResponse({"ok": True, "users": items})


@login_required
@require_http_methods(["POST"])
def job_toggle_hidden(request, job_id: int):
    """
    Скрыть/показать свою обработку (GenerationJob) на странице профиля.
    - Доступно только владельцу job.
    - Публикации, выложенные в галерею (PublicPhoto/PublicVideo is_active=True), не скрываются от других — кнопку для них не показываем в UI.
    Out JSON: { ok: true, hidden: bool }
    """
    from generate.models import GenerationJob
    from gallery.models import JobHide, PublicPhoto, PublicVideo

    try:
        job = GenerationJob.objects.get(pk=job_id)
    except GenerationJob.DoesNotExist:
        return JsonResponse({"ok": False, "error": "not found"}, status=404)

    if not job.user_id or job.user_id != request.user.id:
        return JsonResponse({"ok": False, "error": "forbidden"}, status=403)


    rel = JobHide.objects.filter(user=request.user, job=job).first()
    if rel:
        rel.delete()
        return JsonResponse({"ok": True, "hidden": False})
    else:
        JobHide.objects.create(user=request.user, job=job)
        return JsonResponse({"ok": True, "hidden": True})


@login_required
@require_http_methods(["GET"])
def follow_recommendations(request):
    """
    Рекомендации аккаунтов для подписки (инстаграм-стайл):
    - исключаем уже подписанных
    - сортируем по количеству подписчиков (популярные)
    GET:
      - limit: int (<=20)
    """
    try:
        limit = int(request.GET.get("limit") or "12")
    except Exception:
        limit = 12
    limit = max(1, min(limit, 20))

    User = get_user_model()

    # Уже подписаны
    already_ids = set(Follow.objects.filter(
        follower=request.user).values_list("following_id", flat=True))

    qs = User.objects.exclude(id=request.user.id).exclude(id__in=already_ids) \
        .annotate(followers_count=Count("followers_relations", distinct=True)) \
        .order_by("-followers_count", "username")[:limit]

    user_ids = [u.id for u in qs]
    profiles = {p.user_id: p for p in Profile.objects.filter(
        user_id__in=user_ids)}
    following_counts = dict(
        Follow.objects.filter(follower_id__in=user_ids).values_list(
            "follower_id").annotate(c=Count("id"))
    )
    followers_counts = dict(
        Follow.objects.filter(following_id__in=user_ids).values_list(
            "following_id").annotate(c=Count("id"))
    )

    recs = []
    for u in qs:
        prof = profiles.get(u.id)
        recs.append({
            "username": u.username,
            "name": (u.first_name or "")[:64],
            "avatar_url": getattr(prof.avatar, "url", "") if prof and getattr(prof, "avatar", None) else "",
            "is_following": False,
            "followers": int(followers_counts.get(u.id, 0)),
            "following": int(following_counts.get(u.id, 0)),
        })

    return JsonResponse({"ok": True, "users": recs})


@require_http_methods(["GET"])
def profile_published_feed(request):
    """
    Смешанная лента опубликованных фото и видео для профиля.
    GET:
      - username (опц.) — чей профиль; по умолчанию текущий пользователь
      - limit (опц.) — по умолчанию 60, максимум 120
    Ответ:
      { ok: true, items: [
          {
            "type": "photo"|"video",
            "id": int,
            "created": "ISO8601",
            "media_url": "...",         # image url (photo) или thumbnail (video если есть, иначе "")
            "video_url": "...",         # только для video
            "detail_url": "...",        # детальная страница (для модалки)
            "title": "...",             # если доступно
            "likes": int, "comments": int, "views": int
          }, ...
        ],
        "count": int
      }
    """
    try:
        from django.contrib.auth import get_user_model
        from django.urls import reverse
        from gallery.models import PublicPhoto, PublicVideo, JobHide, PhotoSave, VideoSave
        from generate.templatetags.generate_extras import model_display
    except Exception:
        return JsonResponse({"ok": False, "error": "imports failed"}, status=500)

    username = (request.GET.get("username") or "").strip()
    try:
        limit = int(request.GET.get("limit") or "60")
    except Exception:
        limit = 60
    limit = max(1, min(limit, 120))

    User = get_user_model()
    # Определяем целевого пользователя
    target = request.user
    if username:
        target = User.objects.filter(username=username).first() or \
                 User.objects.filter(username__iexact=username).first() or \
                 request.user

    # Спрятанные задачи владельца (не показываем чужим, даже если публикация активна)
    hidden_ids = []
    try:
        hidden_ids = list(JobHide.objects.filter(user=target).values_list("job_id", flat=True))
    except Exception:
        hidden_ids = []

    # Фото
    try:
        pf_qs = PublicPhoto.objects.filter(is_active=True).filter(Q(uploaded_by=target) | Q(source_job__user=target))
        if request.user.id != getattr(target, "id", None) and hidden_ids:
            # PublicPhoto использует source_job_id как связь к job
            pf_qs = pf_qs.exclude(source_job_id__in=hidden_ids)
        photos = list(pf_qs.only("id", "image", "title", "created_at"))
    except Exception:
        photos = []

    # Видео
    try:
        pv_qs = PublicVideo.objects.filter(is_active=True).filter(Q(uploaded_by=target) | Q(source_job__user=target))
        if request.user.id != getattr(target, "id", None) and hidden_ids:
            pv_qs = pv_qs.exclude(source_job_id__in=hidden_ids)
        videos = list(pv_qs.only("id", "thumbnail", "created_at"))
    except Exception:
        videos = []

    # Saves counts for photos/videos
    photo_save_counts = {}
    video_save_counts = {}
    try:
        photo_ids = [int(p.id) for p in photos]
        if photo_ids:
            for row in PhotoSave.objects.filter(photo_id__in=photo_ids).values("photo_id").annotate(c=Count("id")):
                photo_save_counts[int(row["photo_id"])] = int(row["c"] or 0)
    except Exception:
        photo_save_counts = {}
    try:
        video_ids = [int(v.id) for v in videos]
        if video_ids:
            for row in VideoSave.objects.filter(video_id__in=video_ids).values("video_id").annotate(c=Count("id")):
                video_save_counts[int(row["video_id"])] = int(row["c"] or 0)
    except Exception:
        video_save_counts = {}

    items = []
    # Собираем фото
    for p in photos:
        try:
            media_url = getattr(getattr(p, "image", None), "url", "") or ""
        except Exception:
            media_url = ""
        try:
            title = (getattr(p, "title", "") or "").strip()
        except Exception:
            title = ""
        try:
            durl = p.get_absolute_url()
        except Exception:
            durl = ""
        # Счётчики (если аннотированы где-то ещё, здесь безопасно приводим к int)
        likes = int(getattr(p, "likes_count", 0) or 0)
        comments = int(getattr(p, "comments_count", 0) or 0)
        views = int(getattr(p, "view_count", 0) or 0)
        saves = int(getattr(p, "saves_count", 0) or photo_save_counts.get(int(p.id), 0) or 0)
        # Исходная задача (job) и флаг скрытия
        try:
            job_id_val = getattr(p, "source_job_id", None)
            if job_id_val is None:
                job_id_val = getattr(p, "job_id", None)
            job_id_val = int(job_id_val) if job_id_val is not None else 0
        except Exception:
            job_id_val = 0
        is_hidden = bool(job_id_val and (job_id_val in hidden_ids))

        items.append({
            "type": "photo",
            "id": int(p.id),
            "created": getattr(p, "created_at", None).isoformat() if getattr(p, "created_at", None) else "",
            "media_url": media_url,
            "video_url": "",
            "detail_url": durl,
            "title": title,
            "likes": likes,
            "comments": comments,
            "views": views,
            "saves": saves,
            "model": (model_display(p) or ""),
            "job_id": job_id_val,
            "hidden": is_hidden,
        })

    # Собираем видео
    for v in videos:
        try:
            thumb = getattr(getattr(v, "thumbnail", None), "url", "") or ""
        except Exception:
            thumb = ""
        # в наших шаблонах доступен v.video_url
        try:
            video_url = getattr(v, "video_url", "") or ""
        except Exception:
            video_url = ""
        try:
            durl = v.get_absolute_url()
        except Exception:
            durl = ""

        # title (if available)
        try:
            title = (getattr(v, "title", "") or "").strip()
        except Exception:
            title = ""
        likes = int(getattr(v, "likes_count", 0) or 0)
        comments = int(getattr(v, "comments_count", 0) or 0)
        views = int(getattr(v, "view_count", 0) or 0)
        saves = int(getattr(v, "saves_count", 0) or video_save_counts.get(int(v.id), 0) or 0)
        # Исходная задача (job) и флаг скрытия
        try:
            job_id_val = int(getattr(v, "source_job_id", 0) or 0)
        except Exception:
            job_id_val = 0
        is_hidden = bool(job_id_val and (job_id_val in hidden_ids))

        items.append({
            "type": "video",
            "id": int(v.id),
            "created": getattr(v, "created_at", None).isoformat() if getattr(v, "created_at", None) else "",
            "media_url": thumb,      # как постер
            "video_url": video_url,
            "stream_url": reverse("gallery:video_stream", args=[v.id]),
            "detail_url": durl,
            "title": title,
            "likes": likes,
            "comments": comments,
            "views": views,
            "saves": saves,
            "model": (model_display(v) or ""),
            "job_id": job_id_val,
            "hidden": is_hidden,
        })

    # Сортировка по дате убыванию
    try:
        items.sort(key=lambda x: x.get("created") or "", reverse=True)
    except Exception:
        pass

    if len(items) > limit:
        items = items[:limit]

    return JsonResponse({"ok": True, "items": items, "count": len(items)})


@login_required
@require_http_methods(["GET"])
def follow_list_followers(request):
    """
    Список подписчиков для указанного пользователя (или текущего, если username не передан).
    GET:
      - username: чей список смотреть (опц.)
      - q: фильтр по username/имени
      - limit: максимум 100
    Ответ:
      { ok: true, users: [{username, name, avatar_url, is_following}] }
    """
    from django.contrib.auth import get_user_model

    # Определяем целевого пользователя
    username_in = (request.GET.get("username") or "").strip()
    User = get_user_model()
    target = request.user
    if username_in:
        target = User.objects.filter(username=username_in).first() or User.objects.filter(
            username__iexact=username_in).first() or request.user

    try:
        limit = int(request.GET.get("limit") or "50")
    except Exception:
        limit = 50
    limit = max(1, min(limit, 100))
    q = (request.GET.get("q") or "").strip()

    # Уже подписки ТЕКУЩЕГО пользователя (для флага «подписан ли я на этого»)
    already_following = set(Follow.objects.filter(
        follower=request.user).values_list("following_id", flat=True))

    # Кто подписан на target
    rels = Follow.objects.filter(following=target)
    if q:
        rels = rels.filter(
            Q(follower__username__icontains=q) |
            Q(follower__first_name__icontains=q) |
            Q(follower__last_name__icontains=q)
        )
    rels = rels.select_related("follower").order_by("-created_at")[:limit]

    user_ids = [r.follower_id for r in rels]
    profiles = {p.user_id: p for p in Profile.objects.filter(
        user_id__in=user_ids)}

    items = []
    for r in rels:
        u = r.follower
        prof = profiles.get(u.id)
        items.append({
            "username": u.username,
            "name": (u.first_name or "")[:64],
            "avatar_url": getattr(prof.avatar, "url", "") if prof and getattr(prof, "avatar", None) else "",
            # показываем, подписан ли ТЕКУЩИЙ пользователь на u
            "is_following": u.id in already_following,
        })

    return JsonResponse({"ok": True, "users": items})


@login_required
@require_http_methods(["GET"])
def follow_list_following(request):
    """
    Список подписок указанного пользователя (или текущего, если username не передан).
    GET:
      - username: чей список смотреть (опц.)
      - q: фильтр по username/имени
      - limit: максимум 100
    Ответ:
      { ok: true, users: [{username, name, avatar_url, is_following}] }
    """
    from django.contrib.auth import get_user_model

    # Определяем целевого пользователя
    username_in = (request.GET.get("username") or "").strip()
    User = get_user_model()
    target = request.user
    if username_in:
        target = User.objects.filter(username=username_in).first() or User.objects.filter(
            username__iexact=username_in).first() or request.user

    try:
        limit = int(request.GET.get("limit") or "50")
    except Exception:
        limit = 50
    limit = max(1, min(limit, 100))
    q = (request.GET.get("q") or "").strip()

    rels = Follow.objects.filter(follower=target)
    if q:
        rels = rels.filter(
            Q(following__username__icontains=q) |
            Q(following__first_name__icontains=q) |
            Q(following__last_name__icontains=q)
        )
    rels = rels.select_related("following").order_by("-created_at")[:limit]

    user_ids = [r.following_id for r in rels]
    profiles = {p.user_id: p for p in Profile.objects.filter(
        user_id__in=user_ids)}

    # Подписки текущего пользователя — чтобы отрисовать кнопку «Подписаться/Отписаться»
    current_user_following = set(Follow.objects.filter(
        follower=request.user).values_list("following_id", flat=True))

    items = []
    for r in rels:
        u = r.following
        prof = profiles.get(u.id)
        items.append({
            "username": u.username,
            "name": (u.first_name or "")[:64],
            "avatar_url": getattr(prof.avatar, "url", "") if prof and getattr(prof, "avatar", None) else "",
            # показываем, подписан ли текущий пользователь на u
            "is_following": (u.id in current_user_following),
        })

    return JsonResponse({"ok": True, "users": items})


@login_required
@require_http_methods(["POST"])
def account_change_email(request):
    """
    Смена email текущего пользователя.
    In:
      - email: str
    Out JSON:
      { ok: true, email: str } | { ok: false, error: str }
    """
    User = get_user_model()
    new_email = (request.POST.get("email") or "").strip()
    if not new_email:
        return JsonResponse({"ok": False, "error": "email required"}, status=400)

    try:
        validate_email(new_email)
    except ValidationError:
        return JsonResponse({"ok": False, "error": "invalid email"}, status=400)

    # Uniqueness check (case-insensitive)
    if User.objects.filter(email__iexact=new_email).exclude(pk=request.user.pk).exists():
        return JsonResponse({"ok": False, "error": "email already in use"}, status=409)

    # Save
    user = request.user
    user.email = new_email
    user.save(update_fields=["email"])
    return JsonResponse({"ok": True, "email": new_email})


@login_required
@require_http_methods(["POST"])
def account_change_username(request):
    """
    Смена username текущего пользователя.
    In:
      - username: str
    Rules:
      - 3..30 символов
      - a-z 0-9 _ -
      - уникален
      - запрещенные имена отфильтрованы
    Out JSON:
      { ok: true, username: str, redirect: str } | { ok: false, error: str }
    """
    User = get_user_model()
    new_username = (request.POST.get("username") or "").strip()

    if not new_username:
        return JsonResponse({"ok": False, "error": "username required"}, status=400)

    # Normalize
    new_username = new_username.lower()

    # Validate
    if len(new_username) < 3 or len(new_username) > 30:
        return JsonResponse({"ok": False, "error": "username length 3..30"}, status=400)

    if not re.fullmatch(r"[a-z0-9_-]+", new_username):
        return JsonResponse({"ok": False, "error": "allowed: a-z, 0-9, _ and -"}, status=400)

    reserved = {
        "admin", "login", "logout", "signup", "accounts",
        "dashboard", "gallery", "generate", "blog",
        "api", "static", "media", "profile", "profiles",
    }
    if new_username in reserved:
        return JsonResponse({"ok": False, "error": "username is reserved"}, status=400)

    # Uniqueness
    if User.objects.filter(username__iexact=new_username).exclude(pk=request.user.pk).exists():
        return JsonResponse({"ok": False, "error": "username already taken"}, status=409)

    # Save
    user = request.user
    old_username = user.username
    user.username = new_username
    user.save(update_fields=["username"])

    # Build redirect to new profile
    try:
        redirect_url = f"/profile-{new_username}"
    except Exception:
        redirect_url = "/"

    return JsonResponse({"ok": True, "username": new_username, "redirect": redirect_url})
