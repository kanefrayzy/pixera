#!/usr/bin/env python
"""Скрипт для получения всех активных промптов из базы данных"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_gallery.settings')
django.setup()

from generate.models import CategoryPrompt

prompts = CategoryPrompt.objects.filter(is_active=True).select_related('category').order_by('category__name', 'id')

print(f'Всего активных промптов: {prompts.count()}\n')
print('=' * 80)

for p in prompts:
    category_name = p.category.name if p.category else "Без категории"
    print(f'\nID: {p.id}')
    print(f'Категория: {category_name}')
    print(f'Русский текст: {p.prompt_text}')
    print(f'Английский текст: {p.prompt_en if p.prompt_en else "[ПУСТО - НУЖНО ЗАПОЛНИТЬ]"}')
    print('-' * 80)
