# FILE: gallery/sitemaps.py
from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import PublicPhoto


class GallerySitemap(Sitemap):
    """Gallery images sitemap"""
    changefreq = "weekly"
    priority = 0.6
    protocol = 'https'

    def items(self):
        return PublicPhoto.objects.filter(is_active=True).select_related().only("id", "created_at")

    def lastmod(self, obj):
        return obj.created_at

    def location(self, obj):
        return reverse("gallery:photo_detail", args=[obj.pk])
