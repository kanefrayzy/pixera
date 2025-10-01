# blog/views.py
from __future__ import annotations

import re
import unicodedata
from django.utils import timezone
from django.utils.text import slugify

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from .forms import PostForm
from .models import Post, Tag


# ───────────────────────── Публичные страницы ─────────────────────────

def index(request: HttpRequest) -> HttpResponse:
    q = (request.GET.get("q") or "").strip()
    tag_slug = (request.GET.get("tag") or "").strip()
    sort = request.GET.get("sort") or "new"
    page = request.GET.get("page") or 1
    per_page = 12

    # Показываем только опубликованное и не из будущего
    qs = Post.objects.filter(is_published=True, published_at__lte=timezone.now())

    if q:
        qs = qs.filter(
            Q(title__icontains=q) |
            Q(excerpt__icontains=q) |
            Q(body__icontains=q)
        )

    active_tag = None
    if tag_slug:
        active_tag = Tag.objects.filter(slug=tag_slug).first()
        if active_tag:
            qs = qs.filter(tags=active_tag)

    if sort == "new":
        qs = qs.order_by("-published_at", "-id")

    paginator = Paginator(
        qs.only("id", "slug", "title", "excerpt", "cover", "published_at"),
        per_page
    )
    page_obj = paginator.get_page(page)

    # Облако тегов (популярные сначала)
    tags = (
        Tag.objects.annotate(cnt=Count("posts"))
        .filter(cnt__gt=0)
        .order_by("-cnt", "name")[:30]
    )

    # Query без page — удобно для пагинации
    params = request.GET.copy()
    params.pop("page", None)
    keep_query = params.urlencode()

    ctx = {
        "q": q,
        "tag_slug": tag_slug,
        "active_tag": active_tag,
        "tags": tags,
        "posts": page_obj.object_list,
        "paginator": paginator,
        "page_obj": page_obj,
        "keep_query": keep_query,
        "result_count": paginator.count,
    }
    return render(request, "blog/index.html", ctx)


# ───────────────────────── Детальная страница ─────────────────────────

_SLUG_NUM_RE = re.compile(r"^(?P<base>.+)-(?P<num>\d+)$")

def _find_post(slug: str, include_unpublished: bool = False):
    """
    Ищем пост «умно»: точное совпадение, NFC-нормализация,
    ASCII-слуг, case-insensitive, а также варианты без -N / с меньшими N.
    """
    def base_q():
        qs = Post.objects.all()
        if not include_unpublished:
            qs = qs.filter(is_published=True, published_at__lte=timezone.now())
        return qs

    # кандидаты слуга
    nfc = unicodedata.normalize("NFC", slug or "")
    cand = {slug, nfc}

    ascii_slug = slugify(nfc, allow_unicode=False)
    if ascii_slug:
        cand.add(ascii_slug)

    # пробуем прямые совпадения (и case-insensitive)
    qs = base_q().filter(slug__in=list(cand))
    post = qs.first()
    if post:
        return post

    post = base_q().filter(slug__iexact=nfc).first()
    if post:
        return post

    # если слуг заканчивается на -N — попробуем базу и меньшие номера
    m = _SLUG_NUM_RE.match(nfc)
    if m:
        base = m.group("base")
        try:
            num = int(m.group("num"))
        except ValueError:
            num = None

        if base:
            post = base_q().filter(slug__in=[base, base.lower()]).first()
            if post:
                return post

        if num and num >= 2:
            for n in range(num - 1, 1, -1):
                candn = f"{base}-{n}"
                post = base_q().filter(slug__in=[candn, candn.lower()]).first()
                if post:
                    return post

    return None


def detail(request, slug: str):
    """
    Публика видит только опубликованное.
    Staff/суперпользователь видит и неопубликованное.
    """
    # 1) сначала ищем среди опубликованных
    post = _find_post(slug, include_unpublished=False)
    if post:
        return render(request, "blog/detail.html", {"post": post})

    # 2) staff может смотреть черновики
    if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser):
        post = _find_post(slug, include_unpublished=True)
        if post:
            return render(request, "blog/detail.html", {"post": post})

    # 3) честный 404
    raise Http404("Статья не найдена")


# ───────────────────────── CRUD для staff ─────────────────────────

class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self) -> bool:
        u = self.request.user
        return bool(u and (u.is_staff or u.is_superuser))

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            return HttpResponseForbidden("Доступ только для персонала.")
        return super().handle_no_permission()


class PostCreateView(StaffRequiredMixin, View):
    def get(self, request):  # type: ignore
        return render(request, "blog/form.html", {"form": PostForm(), "mode": "create"})

    def post(self, request):  # type: ignore
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            # commit=False — чтобы выставить автопубликацию для staff
            post = form.save(commit=False)

            # 🔓 staff создаёт — публикуем сразу
            if request.user.is_staff or request.user.is_superuser:
                post.is_published = True
                post.published_at = timezone.now()

            post.save()
            form.save_m2m()

            messages.success(request, "Статья создана.")
            return redirect(post.get_absolute_url())

        messages.error(
            request,
            "Исправьте ошибки: " + "; ".join(f"{k}: {', '.join(v)}" for k, v in form.errors.items())
        )
        return render(request, "blog/form.html", {"form": form, "mode": "create"})


class PostUpdateView(StaffRequiredMixin, View):
    def get(self, request, slug):  # type: ignore
        post = get_object_or_404(Post, slug=slug)
        return render(
            request, "blog/form.html",
            {"form": PostForm(instance=post), "mode": "edit", "post": post}
        )

    def post(self, request, slug):  # type: ignore
        post = get_object_or_404(Post, slug=slug)
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            post = form.save(commit=False)

            # Если staff сохраняет черновик — публикуем и ставим актуальную дату
            if (request.user.is_staff or request.user.is_superuser) and not post.is_published:
                post.is_published = True
                post.published_at = timezone.now()

            post.save()
            form.save_m2m()

            messages.success(request, "Статья обновлена.")
            return redirect(post.get_absolute_url())

        messages.error(
            request,
            "Исправьте ошибки: " + "; ".join(f"{k}: {', '.join(v)}" for k, v in form.errors.items())
        )
        return render(request, "blog/form.html", {"form": form, "mode": "edit", "post": post})


class PostDeleteView(StaffRequiredMixin, View):
    def get(self, request, slug):  # type: ignore
        post = get_object_or_404(Post, slug=slug)
        return render(request, "blog/confirm_delete.html", {"post": post})

    def post(self, request, slug):  # type: ignore
        post = get_object_or_404(Post, slug=slug)
        title = post.title
        post.delete()
        messages.success(request, f"«{title}» удалена.")
        return redirect("blog:index")
