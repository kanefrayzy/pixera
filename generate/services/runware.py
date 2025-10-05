from __future__ import annotations

import json
import logging
import uuid
from typing import Optional, Tuple, Any, Dict, List

import requests
from django.conf import settings

log = logging.getLogger(__name__)


class RunwareError(Exception):
    """Ошибки взаимодействия с Runware API."""


# ───────────────────────────────── helpers ───────────────────────────────── #

def _get_api_url() -> str:
    """Единая точка, POST массивом задач."""
    return getattr(settings, "RUNWARE_API_URL", "https://api.runware.ai/v1").rstrip("/")


def _get_api_key() -> str:
    key = getattr(settings, "RUNWARE_API_KEY", "")
    if not key:
        raise RunwareError("RUNWARE_API_KEY не задан")
    return key


def _headers_with_bearer() -> dict:
    return {"Authorization": f"Bearer {_get_api_key()}", "Content-Type": "application/json"}


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
        if 'prompt' in task and len(str(task['prompt'])) > 2000:
            raise RunwareError("Prompt too long")

    url = _get_api_url()
    try:
        r = requests.post(url, json=tasks, headers=headers or _headers_with_bearer(), timeout=timeout)
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
    steps: int = 28,
    cfg_scale: float = 7.0,
    scheduler: Optional[str] = None,
    webhook_url: Optional[str] = None,
    check_nsfw: Optional[bool] = None,
) -> str:
    """Отправляет задачу (deliveryMethod=async) и возвращает taskUUID."""
    task_uuid = str(uuid.uuid4())
    task: Dict[str, Any] = {
        "taskType": "imageInference",
        "taskUUID": task_uuid,
        "deliveryMethod": "async",
        "outputType": "URL",
        "outputFormat": "JPG",
        "positivePrompt": prompt,
        "prompt": prompt,
        "height": int(height),
        "width": int(width),
        "model": model_id,
        "steps": int(steps),
        "CFGScale": float(cfg_scale),
        "numberResults": 1,
    }
    if scheduler:
        task["scheduler"] = scheduler
    if webhook_url:
        task["webhookURL"] = webhook_url
    if check_nsfw is None:
        check_nsfw = bool(getattr(settings, "RUNWARE_CHECK_NSFW", False))
    if check_nsfw:
        task["checkNSFW"] = True

    try:
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
    *,
    prompt: str,
    model_id: str,
    width: int,
    height: int,
    steps: int = 28,
    cfg_scale: float = 7.0,
    scheduler: Optional[str] = None,
) -> str:
    """Синхронная генерация (deliveryMethod=sync). Возвращает imageURL."""
    task: Dict[str, Any] = {
        "taskType": "imageInference",
        "taskUUID": str(uuid.uuid4()),
        "deliveryMethod": "sync",
        "outputType": "URL",
        "outputFormat": "JPG",
        "positivePrompt": prompt,
        "prompt": prompt,
        "width": int(width),
        "height": int(height),
        "model": model_id,
        "steps": int(steps),
        "CFGScale": float(cfg_scale),
        "numberResults": 1,
    }
    if scheduler:
        task["scheduler"] = scheduler

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
