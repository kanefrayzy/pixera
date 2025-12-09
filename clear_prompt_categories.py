#!/usr/bin/env python
"""Скрипт для очистки категорий промптов перед миграцией"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_gallery.settings')
django.setup()

from generate.models import PromptCategory, CategoryPrompt

# Удаляем все промпты
deleted_prompts = CategoryPrompt.objects.all().delete()
print(f"Удалено промптов: {deleted_prompts[0]}")

# Удаляем все категории
deleted_categories = PromptCategory.objects.all().delete()
print(f"Удалено категорий: {deleted_categories[0]}")

print("Очистка завершена успешно!")
