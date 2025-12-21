#!/usr/bin/env python
"""
Проверка: что сохранилось в video_resolution для последних задач
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_gallery.settings')
django.setup()

from generate.models import GenerationJob

print("\n" + "="*70)
print("ПРОВЕРКА: video_resolution в последних задачах")
print("="*70)

# Последние 5 задач
jobs = GenerationJob.objects.filter(generation_type='image').order_by('-id')[:5]

for job in jobs:
    print(f"\n{'─'*70}")
    print(f"Job #{job.id}")
    print(f"{'─'*70}")
    print(f"Model ID: {job.model_id}")
    print(f"video_resolution: '{job.video_resolution}'")
    print(f"Status: {job.status}")
    if job.error:
        print(f"Error: {job.error[:200]}")
    
    # Попытка распарсить
    if job.video_resolution and 'x' in job.video_resolution.lower():
        try:
            parts = job.video_resolution.lower().split('x')
            if len(parts) == 2:
                w = int(parts[0].strip())
                h = int(parts[1].strip())
                total = w * h
                print(f"✅ Parsed: {w}×{h} = {total:,} pixels")
                
                # Проверка для Seedream
                if job.model_id and 'bytedance:5' in job.model_id.lower():
                    if 3686400 <= total <= 16777216:
                        print(f"   ✅ Seedream OK (в диапазоне 3,686,400 - 16,777,216)")
                    else:
                        print(f"   ❌ Seedream FAIL (вне диапазона 3,686,400 - 16,777,216)")
        except Exception as e:
            print(f"❌ Parse error: {e}")
    else:
        print(f"⚠️ No video_resolution or invalid format")

print(f"\n{'='*70}\n")
