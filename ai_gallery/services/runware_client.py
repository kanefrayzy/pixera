import requests, uuid
from django.conf import settings

class RunwareError(Exception):
    pass

def generate_image_via_rest(prompt: str, model_id: str | None, width=1024, height=1024, number_results=1):
    if not settings.RUNWARE_API_KEY:
        raise RunwareError("RUNWARE_API_KEY not configured")

    model = model_id or settings.RUNWARE_DEFAULT_MODEL
    if model not in settings.RUNWARE_ALLOWED_MODELS:
        raise RunwareError("Model is not allowed")

    payload = [{
        "taskType": "imageInference",
        "taskUUID": str(uuid.uuid4()),
        "positivePrompt": prompt,
        "width": width,
        "height": height,
        "model": model,
        "numberResults": number_results,
        "outputType": "URL",
        "checkNSFW": bool(settings.RUNWARE_CHECK_NSFW),
    }]
    r = requests.post(
        settings.RUNWARE_API_URL,
        json=payload,
        headers={
            "Authorization": f"Bearer {settings.RUNWARE_API_KEY}",
            "Content-Type": "application/json",
        },
        timeout=60,
    )
    r.raise_for_status()
    data = r.json()
    items = data.get("data") or []
    urls = [it["imageURL"] for it in items if it.get("imageURL")]
    if not urls:
        raise RunwareError(f"No images: {data}")
    return urls
