from django import template
from django.utils.safestring import mark_safe
import re

register = template.Library()

@register.filter(name="add_class")
def add_class(field, css_classes):
    """
    Добавляет классы к виджету. Работает как с BoundField, так и с уже-рендеренным SafeString.
    Пример: {{ form.email|add_class:"input big" }}
    """
    # 1) Если это BoundField, рендерим через as_widget с обновлёнными attrs
    if hasattr(field, "as_widget"):
        # Сохраняем уже заданные атрибуты виджета
        base_attrs = getattr(field.field.widget, "attrs", {}) or {}
        existing = base_attrs.get("class", "")
        joined = f"{existing} {css_classes}".strip()
        attrs = {**base_attrs, "class": joined}
        return field.as_widget(attrs=attrs)

    # 2) Если это уже HTML (SafeString/str) — аккуратно внедряем class
    html = str(field)

    # есть class="..." — дописываем
    if 'class="' in html:
        html = re.sub(
            r'class="([^"]*)"',
            lambda m: f'class="{(m.group(1) + " " + css_classes).strip()}"',
            html,
            count=1,
        )
    else:
        # вставляем class перед '>' в первом открывающем теге
        html = re.sub(
            r'(<\w+\b)([^>]*?)>',
            rf'\1\2 class="{css_classes}">',
            html,
            count=1,
        )

    return mark_safe(html)
