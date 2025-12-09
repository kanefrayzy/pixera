# FILE: blog/sitemaps.py
from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Post


class BlogSitemap(Sitemap):
    """Blog posts sitemap"""
    changefreq = "weekly"
    priority = 0.7
    protocol = 'https'

    def items(self):
        return Post.objects.filter(is_published=True).only("slug", "created_at", "updated_at")

    def lastmod(self, obj):
        return obj.updated_at or obj.created_at

    def location(self, obj):
        return reverse("blog:detail", args=[obj.slug])
