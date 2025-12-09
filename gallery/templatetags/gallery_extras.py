from __future__ import annotations
from typing import Any, Mapping, Sequence, MutableMapping
from django import template

register = template.Library()

@register.filter(name="get_item")
def get_item(mapping: Any, key: Any) -> Any:
    """
    Safe dict-like access in templates:
      {{ my_dict|get_item:some_id|default:0 }}
    Works for dicts, QueryDict-like, and sequences (fallback by index).
    """
    if mapping is None:
        return None
    # dict-like
    if isinstance(mapping, dict):
        return mapping.get(key)
    # Mapping (e.g., defaultdict or custom)
    if isinstance(mapping, Mapping):
        try:
            return mapping.get(key)
        except Exception:
            return None
    # Sequence by index
    if isinstance(mapping, (list, tuple)) and isinstance(key, int):
        try:
            return mapping[key]
        except Exception:
            return None
    # Try generic __getitem__
    try:
        return mapping[key]  # type: ignore[index]
    except Exception:
        return None
