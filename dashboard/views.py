# FILE: dashboard/views.py
from __future__ import annotations

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.text import slugify
from django.core.paginator import Paginator
from django.db.models import Q# ← добавлено
from django.db.models import Count

from .models import Wallet
from generate.models import GenerationJob
from gallery.models import PublicPhoto

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
def index(request: HttpRequest) -> HttpResponse:
    wallet, _ = Wallet.objects.get_or_create(user=request.user)
    price = _price_for_user(request.user)
    gens_left, inf = _gens_left_for_wallet(request.user, wallet, price)

    # Последняя активность: 5 последних задач пользователя
    recent_jobs = []
    try:
        qs = (
            GenerationJob.objects
            .filter(user=request.user)
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
    }
    return render(request, "dashboard/index.html", ctx)



@login_required
def my_jobs(request):
    """
    Мои обработки.
    - 15 карточек на страницу.
    - Для каждой завершённой задачи приклеиваем инфо о публикации в галерее
      (бейдж + лайки/комменты/просмотры) только если фото реально активно.
    - Совместимо с моделями, где связь в PublicPhoto называется source_job ИЛИ job.
    - Возвращаем jobs_cards=[{"obj": job, "pub": {...}|None, "is_published": bool}, ...]
    """
    wallet, _ = Wallet.objects.get_or_create(user=request.user)

    qs = (
        GenerationJob.objects
        .filter(user=request.user, status=GenerationJob.Status.DONE)
        .order_by("-created_at")
    )

    paginator = Paginator(qs, 15)
    page_obj = paginator.get_page(request.GET.get("page") or 1)
    jobs = list(page_obj.object_list)

    # Определяем имя поля связи в PublicPhoto: source_job или job
    rel_name = None
    pf_names = {f.name for f in PublicPhoto._meta.get_fields()}
    if "source_job" in pf_names:
        rel_name = "source_job"
    elif "job" in pf_names:
        rel_name = "job"

    pub_by_job_id = {}
    if jobs and rel_name:
        job_ids = [j.id for j in jobs]

        # Пример: {"source_job__in": job_ids, "is_active": True} или {"job__in": job_ids, ...}
        filter_kwargs = {f"{rel_name}__in": job_ids, "is_active": True}

        published = (
            PublicPhoto.objects
            .filter(**filter_kwargs)
            .annotate(
                num_likes=Count("likes", distinct=True),
                num_comments=Count("comments", distinct=True),
            )
            .only("id", rel_name, "view_count", "title", "image")
        )

        # key_attr == "source_job_id" или "job_id"
        key_attr = f"{rel_name}_id"
        pub_by_job_id = {getattr(p, key_attr): p for p in published}

    cards = []
    for j in jobs:
        p = pub_by_job_id.get(j.id)
        if p:
            cards.append({
                "obj": j,
                "is_published": True,
                "pub": {
                    "id": p.id,
                    "likes": int(getattr(p, "num_likes", 0) or 0),
                    "comments": int(getattr(p, "num_comments", 0) or 0),
                    "views": int(getattr(p, "view_count", 0) or 0),
                    "image_url": getattr(p.image, "url", None),
                    "detail_url_name": "gallery:photo_detail",
                },
            })
        else:
            cards.append({"obj": j, "is_published": False, "pub": None})

    return render(
        request,
        "gallery/my_jobs.html",
        {
            "jobs_cards": cards,
            "wallet": wallet,
            "page_obj": page_obj,
            "paginator": paginator,
            "keep_query": "",
        },
    )

@login_required
def tips(request: HttpRequest) -> HttpResponse:
    return render(request, "dashboard/tips.html")

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
    price = _price_for_user(request.user) if request.user.is_authenticated else TOKEN_COST
    gens_left = 0
    inf = ""
    if request.user.is_authenticated:
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        gens_left, inf = _gens_left_for_wallet(request.user, wallet, price)

    plans = [{"id": k, **v} for k, v in PLANS.items()]
    plans.sort(key=lambda p: (p.get("unlimited", False), p["tokens"] if p["tokens"] is not None else 10**9))
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
        messages.info(request, "Чтобы пополнить баланс, авторизуйтесь на нашем сайте.")
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
def purchase_pay(request: HttpRequest, plan_id: str):
    if request.method != "POST":
        return redirect("dashboard:purchase_checkout", plan_id=plan_id)
    plan = _get_plan_or_404(plan_id)
    wallet, _ = Wallet.objects.get_or_create(user=request.user)
    if plan.get("unlimited"):
        wallet.balance = 10_000_000
        wallet.save(update_fields=["balance"])
        messages.success(request, "Безлимит активирован (заглушка).")
    else:
        wallet.topup(int(plan["tokens"]))
        messages.success(request, f"Зачислено {plan['tokens']} TOK (заглушка).")
    return redirect("dashboard:balance")
