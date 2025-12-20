# generate/templatetags/generate_extras.py
from django import template
from django.templatetags.static import static
from django.db.models.fields.files import FileField
from django.utils.text import slugify
import re

register = template.Library()

PREFERRED_FIELDS = ("result", "output", "image", "file")

# Human-friendly names for known model_ids (lowercase keys)
MODEL_NAME_OVERRIDES = {
    # Video models (as shown in UI)
    "runware:201@1": "Wan2.5‑Preview",
    "bytedance:1@1": "ByteDance 1.1",
    "vidu:1@5": "Vidu 1.5",
    "vidu:1@1": "Vidu Q1 I2V",
    "openai:3@2": "Sora 2 Pro",
    "google:3@0": "Veo 3.0",
    "google:2@0": "Veo 2.0",
    "pixverse:1@0": "PixVerse",

    # Image models (as shown on the image generation page)
    "runware:101@1": "Стандартная",
    "runware:108@22": "Face Retouch",
    "bytedance:5@0": "Seedream",
    "bfl:2@2": "FLUX.1.1 [pro] Ultra",
    "rundiffusion:130@100": "Стандартная",
}

# Canonicalize displayed model names regardless of the source (DB name, overrides, raw)
_CANONICAL_RENAME_PATTERNS = (
    (r"\brun\s*diffusion\b", True),
    (r"\brundiffusion\b", True),
    (r"\brundiffussiun\b", True),  # user-typed variant
)

def _canonicalize_name(name: str) -> str:
    """
    Map provider-native labels to site-friendly ones, with safety for typos.
    Example: any 'RunDiffusion 1.30' variants -> 'Стандартная'.
    """
    try:
        src = (name or "").strip()
        lo = re.sub(r"\s+", " ", src.lower())
        if (any(re.search(p, lo) for p, _ in _CANONICAL_RENAME_PATTERNS)
                and ("1.30" in lo or "1.3" in lo)):
            return "Стандартная"
        return src
    except Exception:
        return name

@register.filter
def job_thumb_url(job):
    """
    Возвращает URL любого файла-результата у джоба.
    1) пробуем популярные имена полей,
    2) затем проходим по всем FileField,
    3) иначе — плейсхолдер.
    """
    # 1) привычные имена
    for name in PREFERRED_FIELDS:
        f = getattr(job, name, None)
        url = getattr(f, "url", None)
        if url:
            return url

    # 2) любые FileField
    for field in getattr(job, "_meta").fields:
        if isinstance(field, FileField):
            f = getattr(job, field.name, None)
            url = getattr(f, "url", None)
            if url:
                return url

    # 3) плейсхолдер (положите файл в static/img/placeholder.png)
    return static("img/placeholder.png")


@register.filter
def safe_slugify(value):
    """
    Безопасная slugification с поддержкой кириллицы.
    Если обычный slugify возвращает пустую строку, используем fallback.
    """
    if not value:
        return "untitled"

    # Попробуем обычный slugify
    slug = slugify(value)

    # Если пустой (кириллица), используем transliteration
    if not slug:
        # Простая транслитерация основных кириллических символов
        translit_map = {
            'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
            'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
            'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
            'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
            'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
            ' ': '-', '_': '-'
        }

        # Приводим к нижнему регистру и транслитерируем
        text = value.lower()
        transliterated = ''
        for char in text:
            transliterated += translit_map.get(char, char)

        # Удаляем недопустимые символы и создаем slug
        slug = re.sub(r'[^a-zA-Z0-9\-_]', '', transliterated)
        slug = re.sub(r'[-_]+', '-', slug)  # Убираем повторяющиеся дефисы
        slug = slug.strip('-')  # Убираем дефисы в начале и конце

        # Если всё равно пустой, используем fallback
        if not slug:
            slug = "untitled"

    # Ограничиваем длину
    return slug[:50] if slug else "untitled"


# ===== Model display helpers =====
from typing import Any
try:
    # Import lazily-safe; Django will load this templatetag after apps are ready
    from generate.models import VideoModel  # type: ignore
except Exception:  # pragma: no cover
    VideoModel = None  # type: ignore


def _lookup_model_name_by_id(model_id: str) -> str:
    """
    Resolve site-friendly model name in priority:
      1) ImageModelConfiguration table by model_id (title or name)
      2) VideoModel table by model_id (title or name)
      3) Hard-coded overrides (popular image/video ids used in UI)
      4) Raw model_id
    """
    mid = (model_id or "").strip()
    if not mid:
        return ""
    
    # 1) Check ImageModelConfiguration first
    try:
        from generate.models_image import ImageModelConfiguration
        img_model = ImageModelConfiguration.objects.filter(model_id=mid).first()
        if img_model:
            # Prefer title over name
            title = getattr(img_model, "title", None)
            if title:
                return _canonicalize_name(title)
            name = getattr(img_model, "name", None)
            if name:
                return _canonicalize_name(name)
    except Exception:
        pass
    
    # 2) Check VideoModel
    try:
        if VideoModel is not None:
            vm = VideoModel.objects.filter(model_id=mid).first()
            if vm:
                # Prefer title over name
                title = getattr(vm, "title", None)
                if title:
                    return _canonicalize_name(title)
                name = getattr(vm, "name", None)
                if name:
                    return _canonicalize_name(name)
    except Exception:
        pass
    
    # 3) UI overrides
    try:
        return _canonicalize_name(MODEL_NAME_OVERRIDES.get(mid.lower(), mid))
    except Exception:
        return mid


def _model_display_from(obj: Any) -> str:
    """
    Robust resolver that returns a human-friendly model name for:
      - GenerationJob (image/video)
      - Gallery video/photo objects (via .source_job, .video_model, .model_id)
      - Plain model_id string
    Priority:
      1) explicit job.model_name (if exists)
      2) related .video_model.name
      3) lookup by .model_id in VideoModel
      4) other known fields (image_model/model/provider) as a fallback
    """
    # String-like: treat as model_id
    if isinstance(obj, str):
        return _lookup_model_name_by_id(obj)

    # Dict-like with possible keys
    try:
        if isinstance(obj, dict):
            if obj.get("model_name"):
                return str(obj.get("model_name"))
            if obj.get("video_model") and getattr(obj.get("video_model"), "name", ""):
                return str(getattr(obj.get("video_model"), "name"))
            if obj.get("model_id"):
                return _lookup_model_name_by_id(str(obj.get("model_id")))
            if obj.get("image_model"):
                return _lookup_model_name_by_id(str(obj.get("image_model")))
    except Exception:
        pass

    # Object with attributes
    try:
        # 1) explicit job.model_name (image pipeline sometimes sets this)
        name = getattr(obj, "model_name", None)
        if name:
            return _canonicalize_name(str(name))

        # 2) related video_model (check title first, then name)
        vm = getattr(obj, "video_model", None)
        if vm:
            title = getattr(vm, "title", None)
            if title:
                return _canonicalize_name(str(title))
            name = getattr(vm, "name", None)
            if name:
                return _canonicalize_name(str(name))

        # 3) model_id -> lookup
        mid = getattr(obj, "model_id", None)
        if mid:
            return _lookup_model_name_by_id(str(mid))

        # 4) check source_job (on gallery/public objects)
        sj = getattr(obj, "source_job", None)
        if sj:
            return _model_display_from(sj)

        # 5) some image jobs use image_model/model/provider fields
        for attr in ("image_model", "model", "provider"):
            v = getattr(obj, attr, None)
            if v:
                if isinstance(v, str):
                    return _lookup_model_name_by_id(v)
                return str(v)
    except Exception:
        pass

    return ""


@register.filter(name="model_display")
def model_display(obj: Any) -> str:
    """
    Template filter: {{ job|model_display }} or {{ model_id|model_display }}
    Returns a site-friendly model name everywhere in templates.
    """
    try:
        return _model_display_from(obj) or ""
    except Exception:
        try:
            return str(obj)
        except Exception:
            return ""
