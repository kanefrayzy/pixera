#!/usr/bin/env python
"""Скрипт для проверки оставшихся промптов без английского перевода"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_gallery.settings')
django.setup()

from generate.models import CategoryPrompt
from django.db import models

# Получаем промпты без английского перевода
prompts_without_en = CategoryPrompt.objects.filter(
    is_active=True
).filter(
    models.Q(prompt_en='') | models.Q(prompt_en__isnull=True)
).select_related('category').order_by('category__name', 'id')

print(f'Промптов без английского перевода: {prompts_without_en.count()}\n')
print('=' * 80)

for p in prompts_without_en:
    category_name = p.category.name if p.category else "Без категории"
    print(f'\nID: {p.id}')
    print(f'Категория: {category_name}')
    print(f'Русский текст: {p.prompt_text}')
    print('-' * 80)
