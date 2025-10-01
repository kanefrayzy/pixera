# generate/templatetags/seo.py
from django import template
from ..utils.seo import generate_seo_slug

register = template.Library()

@register.filter
def seo_slug(value):
    return generate_seo_slug(value or "")
