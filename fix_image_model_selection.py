"""
Исправление выбора модели изображений
Проблема: ImageFieldManager не вызывается при выборе модели
"""

# Проверим, что происходит в браузере
print("""
ДИАГНОСТИКА ПРОБЛЕМЫ С ВЫБОРОМ МОДЕЛИ ИЗОБРАЖЕНИЙ
==================================================

Проблема: При клике на карточку модели не обновляются поля формы

Возможные причины:
1. ❌ JSON в data-config не парсится
2. ❌ ImageFieldManager не инициализирован
3. ❌ Функция select() не вызывает updateFieldsForModel

РЕШЕНИЕ:
--------
В templates/generate/new.html в функции select() уже добавлен код:

```javascript
// Обновляем поля через ImageFieldManager
if (card.dataset.config) {
  try {
    const config = JSON.parse(card.dataset.config);
    if (window.imageFieldManager) {
      window.imageFieldManager.updateFieldsForModel(config);
    } else if (typeof ImageFieldManager !== 'undefined') {
      window.imageFieldManager = new ImageFieldManager();
      window.imageFieldManager.updateFieldsForModel(config);
    }
  } catch (e) {
    console.error('Error updating image fields:', e);
  }
}
```

ПРОВЕРКА В БРАУЗЕРЕ:
-------------------
1. Откройте /generate/new
2. Откройте DevTools (F12)
3. В Console выполните:
   ```
   // Проверить, что ImageFieldManager загружен
   console.log('ImageFieldManager:', typeof ImageFieldManager);
   console.log('window.imageFieldManager:', window.imageFieldManager);

   // Проверить data-config первой карточки
   const card = document.querySelector('.image-model-card');
   console.log('Card:', card);
   console.log('Config:', card?.dataset.config);

   // Попробовать распарсить
   try {
     const config = JSON.parse(card.dataset.config);
     console.log('Parsed config:', config);
     console.log('optional_fields:', config.optional_fields);
   } catch(e) {
     console.error('Parse error:', e);
   }
   ```

4. Кликните на карточку модели и проверьте в Console:
   ```
   // Должно быть сообщение об обновлении полей
   // Если нет - значит select() не вызывается или есть ошибка
   ```

ЕСЛИ ПРОБЛЕМА СОХРАНЯЕТСЯ:
-------------------------
Возможно, скрипт image-field-manager.js загружается ПОСЛЕ того, как
выполняется код выбора модели. Нужно убедиться, что:

1. image-field-manager.js подключен БЕЗ defer/async
2. Или инициализация происходит в DOMContentLoaded

Текущий код в new.html подключает скрипт с defer:
<script src="{% static 'js/image-field-manager.js' %}?v={{ STATIC_VERSION }}" defer></script>

Это может вызывать race condition. Попробуйте убрать defer.
""")
