from __future__ import annotations

import json
import logging
import os
import uuid
from typing import Optional, Tuple, Any, Dict, List

import requests
from django.conf import settings
from dotenv import load_dotenv

log = logging.getLogger(__name__)


class RunwareError(Exception):
    """Ошибки взаимодействия с Runware API."""


# ───────────────────────────────── helpers ───────────────────────────────── #

def _get_api_url() -> str:
    """Единая точка, POST массивом задач."""
    return getattr(settings, "RUNWARE_API_URL", "https://api.runware.ai/v1").rstrip("/")


def _get_api_key() -> str:
    """
    Динамически загружает API ключ из .env файла.
    Это позволяет обновлять ключ без перезапуска сервера.
    """
    # Перезагружаем .env файл для получения актуального значения
    load_dotenv(override=True)
    key = os.getenv("RUNWARE_API_KEY", "")
    if not key:
        raise RunwareError("RUNWARE_API_KEY не задан")
    return key


def _headers_with_bearer() -> dict:
    return {"Authorization": f"Bearer {_get_api_key()}", "Content-Type": "application/json"}

def _normalize_ref_images(refs: Optional[List[Any]]) -> List[Any]:
    """
    Runware imageInference referenceImages accepts:
      - a UUID v4 string of a previous upload (many endpoints also accept {"imageUUID": "<uuid>"})
      - or an object: {"imageURL": "https://..."}
    Для совместимости формируем объекты:
      • UUID -> {"imageUUID": "..."}
      • URL  -> {"imageURL": "..."}
    """
    out: List[Any] = []
    if not refs:
        return out
    import re
    uuid_re = re.compile(r"^[0-9a-fA-F]{8}\-[0-9a-fA-F]{4}\-[0-9a-fA-F]{4}\-[0-9a-fA-F]{4}\-[0-9a-fA-F]{12}$")
    for r in refs:
        if isinstance(r, str):
            s = r.strip()
            if not s:
                continue
            if uuid_re.match(s):
                out.append({"imageUUID": s})
            elif s.startswith("http://") or s.startswith("https://"):
                out.append({"imageURL": s})
        elif isinstance(r, dict):
            # keep as-is if already valid keys; also allow imageBase64
            if "imageUUID" in r or "imageURL" in r or "imageBase64" in r:
                out.append(r)
            else:
                for k in ("uuid", "imageUrl", "url", "base64", "image"):
                    v = r.get(k)
                    if isinstance(v, str) and v.strip():
                        if k in ("uuid",):
                            out.append({"imageUUID": v.strip()})
                        elif k in ("base64", "image"):
                            out.append({"imageBase64": v.strip()})
                        else:
                            out.append({"imageURL": v.strip()})
                        break
    return out


def _parse_response(resp: requests.Response) -> dict:
    txt = (resp.text or "")[:4000]
    status = resp.status_code
    if status == 401:
        raise RunwareError("401 Unauthorized от Runware")
    try:
        resp.raise_for_status()
    except requests.HTTPError as e:
        raise RunwareError(f"HTTP {status}: {txt}") from e
    try:
        data = resp.json()
    except Exception as e:
        raise RunwareError(f"Некорректный JSON Runware: {txt}") from e
    if isinstance(data, dict) and data.get("errors"):
        raise RunwareError(f"Runware error: {data.get('errors')}")
    return data


def _post(tasks: List[Dict[str, Any]], timeout: Tuple[int, int] = (10, 60), headers: Optional[dict] = None) -> dict:
    """Отправка массива задач. timeout=(connect, read)."""
    if not tasks or len(tasks) > 10:  # Ограничение на количество задач
        raise RunwareError("Invalid tasks count")

    # Валидация каждой задачи
    for task in tasks:
        if not isinstance(task, dict):
            raise RunwareError("Invalid task format")

        # Проверка на потенциально опасные поля
        if 'positivePrompt' in task and len(str(task['positivePrompt'])) > 2000:
            raise RunwareError("Prompt too long")

    url = _get_api_url()

    # Детальное логирование для отладки
    log.debug("Runware API request to %s", url)
    log.debug("Request payload: %s", json.dumps(tasks, indent=2)[:2000])

    try:
        r = requests.post(url, json=tasks, headers=headers or _headers_with_bearer(), timeout=timeout)
        log.debug("Response status: %s", r.status_code)
        log.debug("Response body: %s", r.text[:2000])
        return _parse_response(r)
    except requests.exceptions.Timeout:
        raise RunwareError("Request timeout")
    except requests.exceptions.ConnectionError:
        raise RunwareError("Connection error")


# ───────────────────────────── public operations ─────────────────────────── #

def submit_image_inference_async(
    *,
    prompt: str,
    model_id: str,
    width: int = 1024,
    height: int = 1024,
    steps: int = 33,
    cfg_scale: float = 3.1,
    scheduler: Optional[str] = "Euler Beta",
    webhook_url: Optional[str] = None,
    check_nsfw: Optional[bool] = None,
    reference_images: Optional[List[str]] = None,
    acceleration: Optional[str] = None,
    number_results: Optional[int] = None,
) -> str:
    """Отправляет задачу (deliveryMethod=async) и возвращает taskUUID."""
    task_uuid = str(uuid.uuid4())
    special = str(model_id or "").strip().lower() in {"bfl:2@2", "bytedance:5@0", "google:4@2"}
    if special:
        # Flux/Seedream: без steps/CFG/scheduler, и с includeCost, JPEG, outputType=["URL"]
        task: Dict[str, Any] = {
            "taskType": "imageInference",
            "taskUUID": task_uuid,
            "deliveryMethod": "async",
            "outputType": ["URL"],
            "outputFormat": "JPEG",
            "positivePrompt": prompt,
            "height": int(height),
            "width": int(width),
            "model": model_id,
            "numberResults": 1,
            "includeCost": True,
        }
        if number_results is not None:
            task["numberResults"] = int(number_results)
    else:
        task: Dict[str, Any] = {
            "taskType": "imageInference",
            "taskUUID": task_uuid,
            "deliveryMethod": "async",
            "outputType": "URL",
            "outputFormat": "JPG",
            "positivePrompt": prompt,
            "height": int(height),
            "width": int(width),
            "model": model_id,
            "steps": int(steps),
            "CFGScale": float(cfg_scale),
            "numberResults": 1,
        }
        if scheduler:
            task["scheduler"] = scheduler
        if number_results is not None:
            task["numberResults"] = int(number_results)
    if webhook_url:
        task["webhookURL"] = webhook_url
    if check_nsfw is None:
        check_nsfw = bool(getattr(settings, "RUNWARE_CHECK_NSFW", False))
    if check_nsfw:
        task["checkNSFW"] = True

    # Reference images support (according to official Runware API docs)
    if reference_images:
        model_lower = str(model_id or "").strip().lower()

        # Models that support referenceImages parameter
        # FLUX.1 Kontext: runware:106@1 (max 2 images)
        # Ace++: runware:102@1
        # Face Retouch: runware:108@22
        # Google Imagen: google:4@2
        if model_lower in {"runware:106@1", "runware:102@1", "runware:108@22"}:
            # Нормализуем в формат, который ожидает Runware:
            #  - UUID  -> {"imageUUID": "..."}
            #  - URL   -> {"imageURL": "..."}
            #  - уже подготовленные dict'ы пропускаем как есть
            refs_norm = _normalize_ref_images(reference_images)
            max_refs = 2 if model_lower == "runware:106@1" else 1
            refs_norm = refs_norm[:max_refs]
            if refs_norm:
                task["referenceImages"] = refs_norm
                log.info(f"Added {len(task['referenceImages'])} reference images for {model_id}")
            else:
                log.warning(f"Reference images provided but none valid after normalization for model {model_id}")
        elif model_lower == "google:4@2":
            # Google Imagen requires CDN URLs as plain strings (not objects)
            from ai_gallery.services.runware_client import runware_image_url
            import re
            uuid_re = re.compile(r"^[0-9a-fA-F]{8}\-[0-9a-fA-F]{4}\-[0-9a-fA-F]{4}\-[0-9a-fA-F]{4}\-[0-9a-fA-F]{12}$")
            cdn_urls = []
            for ref in reference_images:
                if isinstance(ref, str):
                    if uuid_re.match(ref.strip()):
                        cdn_urls.append(runware_image_url(ref.strip()))
                    elif ref.strip().startswith("http"):
                        cdn_urls.append(ref.strip())
            if cdn_urls:
                task["referenceImages"] = cdn_urls[:1]  # Max 1 for Google Imagen
                log.info(f"Added {len(task['referenceImages'])} reference CDN URLs for Google Imagen")
        else:
            # For other models, reference images are NOT supported via referenceImages
            # They would need ControlNet with specific preprocessed guide images
            # We skip adding them to avoid API errors
            log.warning(f"Model {model_id} does not support referenceImages parameter. Skipping {len(reference_images)} reference images.")

    try:
        # Log minimal task details for debugging referenceImages issue
        try:
            log.debug("Runware submit (async) model=%s, hasRef=%s, nRef=%s", model_id, bool(task.get("referenceImages")), len(task.get("referenceImages") or []))
        except Exception:
            pass
        data = _post([task], timeout=(10, 15))
    except RunwareError as e:
        if "401" in str(e):
            auth = {"taskType": "authentication", "apiKey": _get_api_key()}
            data = _post([auth, task], timeout=(10, 15), headers={"Content-Type": "application/json"})
        else:
            raise

    log.debug("Runware async submit: %s", json.dumps(data)[:800])
    arr = data.get("data") or []
    first = arr[0] if isinstance(arr, list) and arr else {}
    return str(first.get("taskUUID") or task_uuid)


def submit_image_inference_sync(
    prompt: str,
    model_id: str,
    *,
    width: int = 1024,
    height: int = 1024,
    steps: int = 20,
    cfg_scale: float = 7.0,
    scheduler: str | None = None,
    reference_images: list[str] | None = None,
    acceleration: str | None = None,
    number_results: int | None = None,
) -> str:
    """Синхронная генерация (deliveryMethod=sync). Возвращает imageURL."""
    special = str(model_id or "").strip().lower() in {"bfl:2@2", "bytedance:5@0", "google:4@2"}
    if special:
        task: Dict[str, Any] = {
            "taskType": "imageInference",
            "taskUUID": str(uuid.uuid4()),
            "deliveryMethod": "sync",
            "outputType": ["URL"],
            "outputFormat": "JPEG",
            "positivePrompt": prompt,
            "width": int(width),
            "height": int(height),
            "model": model_id,
            "numberResults": 1,
            "includeCost": True,
        }
        if number_results is not None:
            task["numberResults"] = int(number_results)
    else:
        task: Dict[str, Any] = {
            "taskType": "imageInference",
            "taskUUID": str(uuid.uuid4()),
            "deliveryMethod": "sync",
            "outputType": "URL",
            "outputFormat": "JPG",
            "positivePrompt": prompt,
            "width": int(width),
            "height": int(height),
            "model": model_id,
            "steps": int(steps),
            "CFGScale": float(cfg_scale),
            "numberResults": 1,
        }
        if scheduler:
            task["scheduler"] = scheduler
        if number_results is not None:
            task["numberResults"] = int(number_results)

    # Reference images support (according to official Runware API docs)
    if reference_images:
        model_lower = str(model_id or "").strip().lower()

        # Models that support referenceImages parameter
        # FLUX.1 Kontext: runware:106@1 (max 2 images)
        # Ace++: runware:102@1
        # Face Retouch: runware:108@22
        # Google Imagen: google:4@2
        if model_lower in {"runware:106@1", "runware:102@1", "runware:108@22"}:
            # Нормализуем в формат, который ожидает Runware:
            #  - UUID  -> {"imageUUID": "..."}
            #  - URL   -> {"imageURL": "..."}
            #  - уже подготовленные dict'ы пропускаем как есть
            refs_norm = _normalize_ref_images(reference_images)
            max_refs = 2 if model_lower == "runware:106@1" else 1
            refs_norm = refs_norm[:max_refs]
            if refs_norm:
                task["referenceImages"] = refs_norm
                log.info(f"Added {len(task['referenceImages'])} reference images for {model_id}")
            else:
                log.warning(f"Reference images provided but none valid after normalization for model {model_id}")
        elif model_lower == "google:4@2":
            # Google Imagen requires CDN URLs as plain strings (not objects)
            from ai_gallery.services.runware_client import runware_image_url
            import re
            uuid_re = re.compile(r"^[0-9a-fA-F]{8}\-[0-9a-fA-F]{4}\-[0-9a-fA-F]{4}\-[0-9a-fA-F]{4}\-[0-9a-fA-F]{12}$")
            cdn_urls = []
            for ref in reference_images:
                if isinstance(ref, str):
                    if uuid_re.match(ref.strip()):
                        cdn_urls.append(runware_image_url(ref.strip()))
                    elif ref.strip().startswith("http"):
                        cdn_urls.append(ref.strip())
            if cdn_urls:
                task["referenceImages"] = cdn_urls[:1]  # Max 1 for Google Imagen
                log.info(f"Added {len(task['referenceImages'])} reference CDN URLs for Google Imagen")
        else:
            # For other models, reference images are NOT supported via referenceImages
            # They would need ControlNet with specific preprocessed guide images
            # We skip adding them to avoid API errors
            log.warning(f"Model {model_id} does not support referenceImages parameter. Skipping {len(reference_images)} reference images.")

    # Debug log before submit
    try:
        has_ref = bool(task.get("referenceImages") or task.get("controlNet"))
        n_ref = len(task.get("referenceImages") or task.get("controlNet") or [])
        log.debug("Runware submit (sync) model=%s, hasRef=%s, nRef=%s", model_id, has_ref, n_ref)
    except Exception:
        pass

    data = _post([task], timeout=(15, 180))
    log.debug("Runware sync submit: %s", json.dumps(data)[:800])

    url = _extract_image_url(data)
    if url:
        return url
    status, url2 = parse_status_and_url(data)
    if status in {"success", "done"} and url2:
        return url2
    raise RunwareError(f"Sync submit returned no URL: {json.dumps(data)[:800]}")


def get_response(task_uuid: str) -> dict:
    """Запросить статус/результат async-задачи (сырой JSON)."""
    req = {"taskType": "getResponse", "taskUUID": str(task_uuid)}
    try:
        data = _post([req], timeout=(10, 20))
    except RunwareError as e:
        if "401" in str(e):
            auth = {"taskType": "authentication", "apiKey": _get_api_key()}
            data = _post([auth, req], timeout=(10, 20), headers={"Content-Type": "application/json"})
        else:
            raise
    log.debug("Runware getResponse(%s): %s", task_uuid, json.dumps(data)[:1200])
    return data


def parse_status_and_url(data: dict) -> Tuple[str, Optional[str]]:
    """
    Унифицированный парсинг:
      - success/done + imageURL → ('success', url)
      - явные ошибки → ('failed', None)
      - иначе → ('running', None)
    """
    if not isinstance(data, dict):
        return "running", None
    if data.get("errors"):
        return "failed", None

    arr = data.get("data")
    if isinstance(arr, list) and arr:
        for item in arr:
            if not isinstance(item, dict):
                continue
            url = (
                item.get("imageURL")
                or item.get("url")
                or (item.get("images") or [{}])[0].get("url")
            )
            if url:
                return "success", str(url)
            st = str(item.get("status") or "").lower()
            if st in {"failed", "error"}:
                return "failed", None
            # если какие-то элементы ещё «processing», продолжаем
        return "running", None

    return "running", None


def _extract_image_url(data: dict) -> Optional[str]:
    """Достаёт URL из популярных форматов ответа."""
    try:
        arr = data.get("data") or []
        if not isinstance(arr, list):
            return None
        for item in arr:
            if not isinstance(item, dict):
                continue
            if isinstance(item.get("imageURL"), str):
                return item["imageURL"]
            if isinstance(item.get("url"), str):
                return item["url"]
            imgs = item.get("images")
            if isinstance(imgs, list) and imgs and isinstance(imgs[0], dict):
                u = imgs[0].get("url")
                if isinstance(u, str):
                    return u
    except Exception:
        pass
    return None


def is_processing(status: Optional[str]) -> bool:
    s = str(status or "").lower()
    return s in {"processing", "running", "queued", "pending", "in_progress", "in-progress"}
