from __future__ import annotations

import re
import secrets
import hashlib
import ipaddress
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponseRedirect


# ────────────────────────────── helpers ──────────────────────────────

def _ensure_session_key(request) -> str:
    if not request.session.session_key:
        request.session.save()
    return request.session.session_key


def _pick_public_ip(parts: list[str]) -> str:
    """Выбрать первый «публичный» IP из списка (игнорируя private/loopback/reserved)."""
    for raw in parts:
        ip = raw.strip()
        if not ip:
            continue
        try:
            obj = ipaddress.ip_address(ip)
            if not (obj.is_private or obj.is_loopback or obj.is_reserved or obj.is_link_local):
                return ip
        except ValueError:
            continue
    return parts[0].strip() if parts else ""


def _client_ip(request) -> str:
    """
    Best-effort IP за прокси/ngrok:
    1) X-Original-Forwarded-For (если есть)
    2) X-Forwarded-For
    3) REMOTE_ADDR
    """
    xoff = (request.META.get("HTTP_X_ORIGINAL_FORWARDED_FOR") or "").strip()
    if xoff:
        parts = [p for p in xoff.split(",") if p.strip()]
        ip = _pick_public_ip(parts) or (parts[0].strip() if parts else "")
        if ip:
            return ip

    xff = (request.META.get("HTTP_X_FORWARDED_FOR") or "").strip()
    if xff:
        parts = [p for p in xff.split(",") if p.strip()]
        ip = _pick_public_ip(parts) or (parts[0].strip() if parts else "")
        if ip:
            return ip

    return (request.META.get("REMOTE_ADDR") or "").strip()


def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _ua_hash(request) -> str:
    ua = (request.META.get("HTTP_USER_AGENT") or "").strip()
    al = (request.META.get("HTTP_ACCEPT_LANGUAGE") or "").strip()
    return _sha256(f"{ua}|{al}")


def _ip_hash(request) -> str:
    ip = _client_ip(request)
    if not ip:
        return ""
    # добавляем SECRET_KEY для усложнения подделки
    return _sha256(f"{ip}|{settings.SECRET_KEY}")


def _hard_fp(request) -> str:
    """Жёсткий fp = H( ua_hash | ip_hash | SECRET_KEY )."""
    return _sha256(f"{_ua_hash(request)}|{_ip_hash(request)}|{settings.SECRET_KEY}")


def _cookie_name_gid() -> str:
    # Важно: backend/views ожидают именно 'gid'
    return "gid"


def _cookie_name_fp() -> str:
    # Соответствует settings.FP_COOKIE_NAME (используется во views)
    return getattr(settings, "FP_COOKIE_NAME", "aid_fp")


def _set_cookie(response, name: str, value: str, *, years: int = 5, http_only: bool = True):
    max_age = int(timedelta(days=365 * years).total_seconds())
    # В деве часто без HTTPS — иначе cookie потеряется. В prod ставим Secure.
    secure = not settings.DEBUG
    samesite = getattr(settings, "SESSION_COOKIE_SAMESITE", "Lax") or "Lax"
    response.set_cookie(
        name,
        value,
        max_age=max_age,
        secure=secure,
        httponly=http_only,
        samesite=samesite,
        path="/",
    )


# ─────────────────────── Age gate (как было) ───────────────────────

class AgeGateMiddleware:
    """
    Ставит флаг request.age_ok из cookie 'age_ok'.
    Показываем плашку 18+ на фронте, если cookie нет И если плашка включена в настройках.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Проверяем cookie возраста
        request.age_ok = request.COOKIES.get("age_ok") == "1"

        # Проверяем, включена ли плашка в настройках
        try:
            from pages.models import SiteSettings
            settings = SiteSettings.get_settings()
            request.age_gate_enabled = settings.age_gate_enabled
            request.age_gate_title = settings.age_gate_title
            request.age_gate_text = settings.age_gate_text

            # Если плашка отключена в настройках, считаем что возраст подтвержден
            if not settings.age_gate_enabled:
                request.age_ok = True
        except Exception:
            # Если настройки недоступны (например, при первом запуске), используем значения по умолчанию
            request.age_gate_enabled = True
            request.age_gate_title = "Вам есть 18 лет?"
            request.age_gate_text = "Доступ к сайту разрешён только пользователям старше 18 лет. Подтвердите возраст для продолжения работы."

        return self.get_response(request)


# ─────────────── Перенаправление языкового префикса ────────────────

class LanguagePrefixRedirectMiddleware:
    """
    Правила:

      • Язык по умолчанию — ru (БЕЗ префикса /ru/).
      • Если путь начинается с /ru/ или ровно /ru — редиректим на путь БЕЗ /ru.
      • Если путь уже с корректным префиксом /en|es|pt|de/ — пропускаем.
      • Если путь без префикса — определяем язык:
          - ?lang=xx или cookie django_language/ui_lang
          - иначе по Accept-Language: en|es|pt|de|ru
          - если неподдерживаемый — en
        и если язык != ru — редиректим на /<lang>/<path>.

    ДОЛЖЕН стоять сразу после SessionMiddleware и ПЕРЕД LocaleMiddleware.
    """

    SUP = ("en", "es", "pt", "de", "ru")
    DEFAULT = "ru"
    LANG_RE = re.compile(r"^/(en|es|pt|de|ru)(/|$)")
    RU_RE = re.compile(r"^/ru(?:/|$)")

    def __init__(self, get_response):
        self.get_response = get_response

        static_url = getattr(settings, "STATIC_URL", "/static/") or "/static/"
        media_url = getattr(settings, "MEDIA_URL", "/media/") or "/media/"
        # Служебные/исключённые префиксы:
        self.skip_prefixes = (
            "/admin/",
            "/i18n/",
            static_url if static_url.startswith("/") else "/" + static_url,
            media_url if media_url.startswith("/") else "/" + media_url,
        )

    @staticmethod
    def _parse_accept_language(header: str) -> list[str]:
        if not header:
            return []
        raw: list[tuple[str, float]] = []
        for part in header.split(","):
            part = part.strip()
            if not part:
                continue
            if ";q=" in part:
                code, q = part.split(";q=", 1)
                try:
                    weight = float(q)
                except Exception:
                    weight = 1.0
            else:
                code, weight = part, 1.0
            base = code.split("-")[0].lower()
            raw.append((base, weight))
        raw.sort(key=lambda x: x[1], reverse=True)
        seen, result = set(), []
        for code, _ in raw:
            if code and code not in seen:
                seen.add(code)
                result.append(code)
        return result

    def _detect_lang(self, request) -> str:
        # 1) ?lang
        param = (request.GET.get("lang") or "").strip().lower()
        if param in self.SUP:
            return param

        # 2) cookie (официальная + фолбэк)
        for cname in ("django_language", "ui_lang"):
            cval = (request.COOKIES.get(cname) or "").strip().lower()
            if cval in self.SUP:
                return cval

        # 3) заголовок браузера
        accept = (request.META.get("HTTP_ACCEPT_LANGUAGE") or "").strip()
        if accept:
            for code in self._parse_accept_language(accept):
                if code in self.SUP:
                    return code
            return "en"

        return self.DEFAULT

    def __call__(self, request):
        path = request.path_info or "/"

        # пропускаем служебные пути
        for pref in self.skip_prefixes:
            if path.startswith(pref):
                return self.get_response(request)

        # 1) Спец-обработка: /ru/... → убрать префикс
        if self.RU_RE.match(path):
            stripped = path[3:] or "/"
            target = stripped if stripped.startswith("/") else "/" + stripped
            if request.META.get("QUERY_STRING"):
                target += "?" + request.META["QUERY_STRING"]
            return HttpResponseRedirect(target)  # 302 достаточно

        # 2) Уже есть языковой префикс
        if self.LANG_RE.match(path):
            return self.get_response(request)

        # 3) Без префикса — решаем
        lang = self._detect_lang(request)
        if lang == self.DEFAULT:
            return self.get_response(request)

        target = f"/{lang}{path}"
        if request.META.get("QUERY_STRING"):
            qs_items = [p for p in request.META["QUERY_STRING"].split("&") if not p.startswith("lang=")]
            if qs_items:
                target += "?" + "&".join(qs_items)
        return HttpResponseRedirect(target)


# ───────────── Новое: устройство/отпечаток и стойкие cookie ─────────────

class DeviceFingerprintMiddleware:
    """
    • Гарантирует session_key.
    • Ставит стойкий cookie 'gid' (HttpOnly) если его нет.
    • Вычисляет:
        ua_hash = H(UA|Accept-Language)
        ip_hash = H(IP|SECRET_KEY)
        fp      = H(ua_hash|ip_hash|SECRET_KEY)
    • Кладёт значения в request (совместимость: request.fp):
        request.device_gid, request.device_fp, request.fp,
        request.device_ip_hash, request.device_ua_hash, request.device_session_key
    • Добавляет ответные заголовки X-Device-Fingerprint, X-Device-GID (для логов).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # session_key должен быть до обработки view
        sess = _ensure_session_key(request)

        # читаем/создаём gid
        gid_cookie_name = _cookie_name_gid()
        gid = (request.COOKIES.get(gid_cookie_name) or "").strip()
        if not gid:
            # 22–32 urlsafe символа — достаточно стойко, <=64 (ограничение у модели)
            gid = secrets.token_urlsafe(22)

        # вычисляем отпечатки
        ua_h = _ua_hash(request)
        ip_h = _ip_hash(request)
        fp = _hard_fp(request)

        # прокинем в request
        request.device_gid = gid
        request.device_fp = fp
        request.fp = fp  # важно для старого кода
        request.device_ip_hash = ip_h
        request.device_ua_hash = ua_h
        request.device_session_key = sess

        # пропускаем дальше и устанавливаем cookie в ответе
        response = self.get_response(request)

        # гарантируем наличие cookie gid (HttpOnly) и вспомогательный cookie с fp (не HttpOnly)
        if request.COOKIES.get(gid_cookie_name) != gid:
            _set_cookie(response, gid_cookie_name, gid, years=5, http_only=True)

        fp_cookie_name = _cookie_name_fp()
        if fp_cookie_name and request.COOKIES.get(fp_cookie_name) != fp:
            _set_cookie(response, fp_cookie_name, fp, years=3, http_only=False)

        # диагностические заголовки
        try:
            response["X-Device-Fingerprint"] = fp[:32]  # усечённый
            response["X-Device-GID"] = gid
        except Exception:
            pass

        return response


# ───────────────────── Новое: мягкий anti-abuse щит ─────────────────────

class AntiAbuseShieldMiddleware:
    """
    Лёгкая преграда до API генерации.
    Реальное ограничение гостя делает FreeGrant/кошелёк.
    Здесь ведём счётчик попыток (скользящее окно) для fp|gid|ip_hash.
    """

    # Пути, которые проверяем жёстче (ендпоинт сабмита)
    WATCH_PATHS = ("/generate/api/submit/",)

    # Лимит попыток за окно
    WINDOW_SECONDS = 60 * 10  # 10 минут
    WINDOW_LIMIT = 12         # попыток сабмита за окно на один ключ (fp/gid/ip_hash)

    def __init__(self, get_response):
        self.get_response = get_response
        self.enabled = bool(getattr(settings, "ENABLE_ANTIABUSE", False))

    def _bump_counter(self, key: str) -> int:
        """Инкремент счётчика в кэше с TTL. Возвращает новое значение."""
        if not key:
            return 0
        ttl = self.WINDOW_SECONDS

        try:
            cache.add(key, 0, ttl)
            return cache.incr(key)
        except ValueError:
            try:
                cur = int(cache.get(key) or 0)
                val = cur + 1
                cache.set(key, val, ttl)
                return val
            except Exception:
                return 0
        except Exception:
            return 0

    def __call__(self, request):
        request.abuse_soft_block = False

        if not self.enabled:
            return self.get_response(request)

        path = request.path_info or "/"
        # проверяем только интересующие POST-пути
        if request.method != "POST" or not any(path.startswith(p) for p in self.WATCH_PATHS):
            return self.get_response(request)

        # соберём ключи
        gid = getattr(request, "device_gid", None) or (request.COOKIES.get(_cookie_name_gid()) or "")
        fp = getattr(request, "device_fp", None) or _hard_fp(request)
        ip_h = getattr(request, "device_ip_hash", None) or _ip_hash(request)

        keys = []
        if fp and len(fp) <= 64:
            keys.append(f"abuse:w:{fp}")
        if gid and len(gid) <= 64:
            keys.append(f"abuse:w_gid:{gid}")
        if ip_h and len(ip_h) <= 64:
            keys.append(f"abuse:w_ip:{ip_h}")

        exceeded = False
        for k in keys:
            val = self._bump_counter(k)
            if val > self.WINDOW_LIMIT:
                exceeded = True

        request.abuse_soft_block = exceeded
        return self.get_response(request)
