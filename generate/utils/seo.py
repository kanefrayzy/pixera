# FILE: generate/utils/seo.py
import re
from typing import Iterable, Optional
from django.utils.text import slugify

# Небольшие стоп-листы для очистки «лишних» слов (RU/EN).
RU_STOP = {
    "и","в","во","не","что","он","она","оно","мы","вы","они","как","а","но","то",
    "на","с","со","по","за","от","из","для","при","у","о","об","обо","же","ли","бы",
    "к","до","над","под","про","это","эти","этот","та","те","тот","так","такой",
    "ещё","уже","тут","там","всё","все","без","есть","быть","будет","были","был"
}
EN_STOP = {
    "a","an","the","and","or","but","of","on","in","to","for","by","with","at","from",
    "is","are","be","been","being","as","that","this","these","those","it","its",
    "into","over","under","about","your","my","our","their","his","her","you"
}

def _tokens(text: str) -> list[str]:
    # Буквы/цифры, включая кириллицу
    return re.findall(r"[A-Za-z0-9\u0400-\u04FF]+", (text or "").lower())

def _truncate_slug(s: str, max_length: int) -> str:
    if len(s) <= max_length:
        return s
    # Режем по дефисам, чтобы не «ломать» слово.
    parts = s.split("-")
    out = []
    for p in parts:
        cand = "-".join(out + [p])
        if len(cand) > max_length:
            break
        out.append(p)
    return "-".join(out)[:max_length].strip("-")

def generate_seo_slug(text: Optional[str], extras: Optional[Iterable[str]] = None, max_length: int = 80) -> str:
    """
    Делает стабильный SEO-slug из произвольного текста:
    - убирает стоп-слова на RU/EN
    - нормализует пробелы/символы
    - безопасная транслитерация через django.slugify
    - ограничение длины по словам (не режем середину)
    """
    base = " ".join([t for t in [text or ""] + list(extras or []) if t]).strip().lower()
    toks = _tokens(base)
    filtered = [t for t in toks if t not in RU_STOP and t not in EN_STOP]
    if not filtered:
        filtered = toks or ["image"]
    # Накапливаем слова и следим за длиной уже после slugify.
    out_words: list[str] = []
    current = ""
    for w in filtered:
        candidate = slugify("-".join(out_words + [w]))
        if not candidate:
            continue
        if len(candidate) <= max_length:
            out_words.append(w)
            current = candidate
        else:
            break
    if not current:
        current = slugify(" ".join(filtered)) or "image"
        current = _truncate_slug(current, max_length)
    return current.strip("-") or "image"

def job_canonical_slug(job) -> str:
    """
    Канонический slug для джоба: строим из промпта и, при желании,
    можно добавить дополнительные атрибуты (модель/стиль и т.п.)
    """
    prompt = getattr(job, "prompt", "") or ""
    return generate_seo_slug(prompt, max_length=80)
