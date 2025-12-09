from django.contrib.sitemaps import Sitemap
from django.urls import reverse


class StaticViewSitemap(Sitemap):
    """Static pages sitemap"""
    changefreq = "weekly"
    priority = 0.8
    protocol = 'https'

    def items(self):
        return [
            'pages:home',
            'pages:about',
            'pages:contact',
            'pages:privacy',
            'gallery:index',
            'gallery:trending',
            'generate:new',
            'blog:index',
        ]

    def location(self, item):
        return reverse(item)

    def lastmod(self, obj):
        from datetime import datetime
        return datetime.now()


class PagesSitemap(Sitemap):
    """Dynamic pages sitemap"""
    changefreq = "monthly"
    priority = 0.7
    protocol = 'https'

    def items(self):
        return []


# Backward compatibility
StaticSitemap = StaticViewSitemap

class ImageSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.6
    protocol = 'https'

    def items(self):
        try:
            from gallery.models import PublicPhoto
            return PublicPhoto.objects.filter(is_active=True).only("id", "created_at")
        except ImportError:
            return []

    def lastmod(self, obj):
        return obj.created_at

    def location(self, obj):
        from django.urls import reverse
        return reverse("gallery:photo_detail", args=[obj.pk])

