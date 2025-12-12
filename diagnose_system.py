#!/usr/bin/env python
"""
Диагностика: проверяем настройки middleware и вызовы функций
"""
import os
import sys
import django

sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_gallery.settings')
django.setup()

from django.conf import settings

print("=" * 70)
print("🔧 ДИАГНОСТИКА MIDDLEWARE И НАСТРОЕК")
print("=" * 70)
print()

# 1. Проверяем MIDDLEWARE
print("📋 MIDDLEWARE список:")
for i, mw in enumerate(settings.MIDDLEWARE, 1):
    is_fp = "DeviceFingerprint" in mw
    marker = "✅ НАЙДЕН!" if is_fp else ""
    print(f"   {i}. {mw} {marker}")
print()

# 2. Проверяем ENABLE_DEVICE_FP
fp_enabled = getattr(settings, 'ENABLE_DEVICE_FP', None)
print(f"⚙️  ENABLE_DEVICE_FP = {fp_enabled}")
if not fp_enabled:
    print("   ❌ ПРОБЛЕМА! ENABLE_DEVICE_FP отключен!")
else:
    print("   ✅ Включен")
print()

# 3. Проверяем настройки cookies
print("🍪 Cookie настройки:")
print(f"   FP_COOKIE_NAME = {getattr(settings, 'FP_COOKIE_NAME', 'aid_fp')}")
print(f"   FP_HEADER_NAME = {getattr(settings, 'FP_HEADER_NAME', 'X-Device-Fingerprint')}")
print(f"   SESSION_COOKIE_SAMESITE = {getattr(settings, 'SESSION_COOKIE_SAMESITE', 'Lax')}")
print()

# 4. Проверяем импорты
print("📦 Проверка импортов:")
try:
    from ai_gallery.middleware import DeviceFingerprintMiddleware
    print("   ✅ DeviceFingerprintMiddleware импортируется")
except ImportError as e:
    print(f"   ❌ Ошибка импорта: {e}")

try:
    from generate.security import ensure_guest_grant_with_security
    print("   ✅ ensure_guest_grant_with_security импортируется")
except ImportError as e:
    print(f"   ❌ Ошибка импорта: {e}")

try:
    from generate.models import DeviceFingerprint
    print("   ✅ DeviceFingerprint модель импортируется")
    print(f"   📊 Полей в модели: {len(DeviceFingerprint._meta.get_fields())}")

    # Проверяем наличие поля server_fp
    fields = [f.name for f in DeviceFingerprint._meta.get_fields()]
    if 'server_fp' in fields:
        print("   ✅ Поле 'server_fp' существует")
    else:
        print("   ❌ Поле 'server_fp' ОТСУТСТВУЕТ! Миграция не применена!")

except ImportError as e:
    print(f"   ❌ Ошибка импорта: {e}")
print()

# 5. Проверяем views
print("🔍 Проверка использования security функций:")
try:
    import inspect
    from generate import views

    # Ищем вызовы ensure_guest_grant_with_security
    source = inspect.getsource(views)
    if 'ensure_guest_grant_with_security' in source:
        print("   ✅ ensure_guest_grant_with_security используется в views")
    else:
        print("   ❌ ensure_guest_grant_with_security НЕ используется в views!")
except Exception as e:
    print(f"   ⚠️  Не удалось проверить: {e}")
print()

# 6. Рекомендации
print("=" * 70)
print("💡 РЕКОМЕНДАЦИИ:")
print("=" * 70)

has_issues = False

# Проверка middleware
if 'DeviceFingerprintMiddleware' not in str(settings.MIDDLEWARE):
    print("❌ КРИТИЧНО: DeviceFingerprintMiddleware не в MIDDLEWARE!")
    print("   Добавьте в settings.py:")
    print("   MIDDLEWARE = [")
    print("       ...")
    print("       'ai_gallery.middleware.DeviceFingerprintMiddleware',")
    print("       ...")
    print("   ]")
    has_issues = True

if not fp_enabled:
    print("❌ КРИТИЧНО: ENABLE_DEVICE_FP = False")
    print("   Установите в settings.py или .env:")
    print("   ENABLE_DEVICE_FP=True")
    has_issues = True

if not has_issues:
    print("✅ Все настройки выглядят правильно!")
    print()
    print("🔧 Следующие шаги:")
    print("1. Перезапустите все контейнеры:")
    print("   docker-compose restart")
    print()
    print("2. Проверьте логи при запуске:")
    print("   docker-compose logs web | grep -i middleware")
    print()
    print("3. Сделайте тестовый запрос и проверьте логи:")
    print("   docker-compose logs -f web")
    print()
    print("4. Проверьте что миграции применены:")
    print("   docker-compose exec web python manage.py showmigrations generate")

print("=" * 70)
