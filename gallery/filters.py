import django_filters
from .models import Image

class ImageFilter(django_filters.FilterSet):
    q = django_filters.CharFilter(method="search", label="Search")
    tag = django_filters.CharFilter(field_name="tags__name", lookup_expr="iexact")

    class Meta:
        model = Image
        fields = ["q","tag","is_public"]

    def search(self, queryset, name, value):
        v = (value or "").strip()
        if len(v) < 2:
            return queryset
        return queryset.filter(title__icontains=v) | queryset.filter(description__icontains=v)

