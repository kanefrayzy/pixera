from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from gallery.models import Image

class StaticSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.8

    def items(self):
        return ["pages", "gallery:index", "gallery:trending", "generate:new"]

    def location(self, item):
        return reverse(item)

class ImageSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.6

    def items(self):
        return Image.objects.filter(is_public=True).only("id", "created_at")

    def lastmod(self, obj):
        return obj.created_at

    def location(self, obj):
        from django.urls import reverse
        return reverse("gallery:detail", args=[obj.pk])

