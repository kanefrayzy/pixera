from __future__ import annotations
from django import template
from ..models import Post

register = template.Library()

@register.inclusion_tag("blog/partials/home_section.html", takes_context=True)
def blog_home_section(context, limit: int = 4):
    posts = (
        Post.objects.filter(is_published=True)
        .only("id","title","slug","cover","excerpt","published_at")
        .order_by("-published_at")[: int(limit or 4) ]
    )
    return {"posts": list(posts), "request": context.get("request")}
