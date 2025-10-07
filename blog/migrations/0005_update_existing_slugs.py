# Generated manually

from django.db import migrations
from blog.utils import transliterate_slug


def update_slugs(apps, schema_editor):
    """Обновляем существующие slug'и с транслитерацией"""
    Post = apps.get_model('blog', 'Post')
    Tag = apps.get_model('blog', 'Tag')

    # Обновляем Post slugs
    for post in Post.objects.all():
        new_slug = transliterate_slug(post.title)
        # Проверяем уникальность
        base_slug = new_slug
        i = 2
        while Post.objects.filter(slug=new_slug).exclude(pk=post.pk).exists():
            new_slug = f"{base_slug}-{i}"
            i += 1

        if post.slug != new_slug:
            post.slug = new_slug
            post.save(update_fields=['slug'])

    # Обновляем Tag slugs
    for tag in Tag.objects.all():
        new_slug = transliterate_slug(tag.name)
        # Проверяем уникальность
        base_slug = new_slug
        i = 2
        while Tag.objects.filter(slug=new_slug).exclude(pk=tag.pk).exists():
            new_slug = f"{base_slug}-{i}"
            i += 1

        if tag.slug != new_slug:
            tag.slug = new_slug
            tag.save(update_fields=['slug'])


def reverse_update_slugs(apps, schema_editor):
    """Обратная операция - не делаем ничего, так как исходные данные могли быть некорректными"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0004_fix_slug_transliteration'),
    ]

    operations = [
        migrations.RunPython(update_slugs, reverse_update_slugs),
    ]
