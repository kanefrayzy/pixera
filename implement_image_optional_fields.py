"""
Автоматическая реализация системы опциональных полей для моделей изображений
"""

def update_view():
    """Обновить generate/views.py для передачи моделей изображений"""

    with open('generate/views.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # Проверить, уже ли добавлен импорт
    if 'from .models_image import ImageModelConfiguration' in content:
        print("✅ Импорт ImageModelConfiguration уже добавлен")
    else:
        # Найти секцию импортов моделей
        import_marker = 'from .models import'
        if import_marker in content:
            pos = content.find(import_marker)
            line_end = content.find('\n', pos)
            import_line = '\nfrom .models_image import ImageModelConfiguration'
            content = content[:line_end] + import_line + content[line_end:]
            print("✅ Добавлен импорт ImageModelConfiguration")
        else:
            print("⚠️  Не найдена секция импортов моделей")

    # Найти функцию new и добавить получение моделей
    func_marker = 'def new(request: HttpRequest) -> HttpResponse:'
    func_pos = content.find(func_marker)

    if func_pos < 0:
        print("❌ Функция new() не найдена")
        return False

    # Проверить, уже ли добавлено получение моделей
    if 'ImageModelConfiguration.objects.filter' in content[func_pos:func_pos+5000]:
        print("✅ Получение моделей изображений уже добавлено")
    else:
        # Найти где создается context
        context_marker = 'context = {'
        context_pos = content.find(context_marker, func_pos)

        if context_pos < 0:
            print("❌ Не найдено создание context")
            return False

        # Добавить получение моделей перед context
        models_code = """
    # Получить активные модели изображений
    image_models = ImageModelConfiguration.objects.filter(is_active=True).order_by('order', 'name')

"""
        content = content[:context_pos] + models_code + content[context_pos:]
        print("✅ Добавлено получение моделей изображений")

        # Обновить позицию context после вставки
        context_pos = content.find(context_marker, func_pos)

    # Добавить image_models в context
    if "'image_models':" in content[context_pos:context_pos+2000]:
        print("✅ image_models уже добавлен в context")
    else:
        # Найти конец context dict
        brace_count = 0
        pos = context_pos + len(context_marker)
        start_pos = pos

        while pos < len(content):
            if content[pos] == '{':
                brace_count += 1
            elif content[pos] == '}':
                if brace_count == 0:
                    # Нашли закрывающую скобку context
                    # Добавить перед ней
                    addition = "        'image_models': image_models,\n    "
                    content = content[:pos] + addition + content[pos:]
                    print("✅ Добавлен image_models в context")
                    break
                brace_count -= 1
            pos += 1

    # Записать обновленный файл
    with open('generate/views.py', 'w', encoding='utf-8') as f:
        f.write(content)

    print()
    print("✅ View обновлен!")
    return True


def update_template():
    """Обновить templates/generate/new.html"""

    with open('templates/generate/new.html', 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Добавить подключение image-field-manager.js
    if 'image-field-manager.js' in content:
        print("✅ image-field-manager.js уже подключен")
    else:
        # Найти где подключается video-field-manager.js
        marker = "static 'js/video-field-manager.js'"
        pos = content.find(marker)
        if pos > 0:
            # Найти конец этой строки
            line_end = content.find('</script>', pos) + len('</script>')
            addition = "\n    <script src=\"{% static 'js/image-field-manager.js' %}\"></script>"
            content = content[:line_end] + addition + content[line_end:]
            print("✅ Добавлено подключение image-field-manager.js")
        else:
            print("⚠️  Не найдено подключение video-field-manager.js")

    # 2. Обновить функцию select(card) для вызова ImageFieldManager
    select_marker = 'function select(card){'
    select_pos = content.find(select_marker)

    if select_pos > 0:
        # Найти localStorage.setItem внутри функции
        localstorage_marker = "localStorage.setItem('gen.image.model'"
        ls_pos = content.find(localstorage_marker, select_pos)

        if ls_pos > 0:
            # Проверить, уже ли добавлен вызов ImageFieldManager
            if 'window.ImageFieldManager' in content[ls_pos:ls_pos+500]:
                print("✅ Вызов ImageFieldManager уже добавлен")
            else:
                # Найти конец строки с localStorage
                line_end = content.find('}catch(_){}', ls_pos) + len('}catch(_){}')

                addition = """

      // Обновить видимость полей на основе конфигурации модели
      if (window.ImageFieldManager && card.dataset.modelConfig) {
        try {
          const modelConfig = JSON.parse(card.dataset.modelConfig);
          if (!window.imageFieldManager) {
            window.imageFieldManager = new window.ImageFieldManager();
          }
          window.imageFieldManager.updateFieldsForModel(modelConfig);
        } catch(e) {
          console.error('Failed to update image fields:', e);
        }
      }"""

                content = content[:line_end] + addition + content[line_end:]
                print("✅ Добавлен вызов ImageFieldManager в select(card)")
        else:
            print("⚠️  Не найден localStorage.setItem в функции select")
    else:
        print("⚠️  Не найдена функция select(card)")

    # Записать обновленный файл
    with open('templates/generate/new.html', 'w', encoding='utf-8') as f:
        f.write(content)

    print()
    print("✅ Шаблон обновлен!")
    print()
    print("⚠️  ВАЖНО: Захардкоженные кнопки моделей НЕ заменены на динамический рендеринг")
    print("   Это нужно сделать вручную, заменив HTML кнопок на:")
    print("   {% for model in image_models %}")
    print("   <button ... data-model-config='{{ model.to_json|safe }}' ...>")
    print("   {% endfor %}")
    return True


if __name__ == '__main__':
    print("Реализация системы опциональных полей для моделей изображений")
    print("="*70)
    print()

    print("Шаг 1: Обновление view...")
    print("-"*70)
    if update_view():
        print()
        print("Шаг 2: Обновление шаблона...")
        print("-"*70)
        if update_template():
            print()
            print("="*70)
            print("✅ Реализация завершена!")
            print()
            print("Следующие шаги:")
            print("1. Создать модели изображений через админ-панель")
            print("2. Настроить optional_fields для каждой модели")
            print("3. Заменить захардкоженные кнопки на динамический рендеринг")
            print("4. Протестировать на /generate/new")
    else:
        print()
        print("❌ Ошибка при обновлении view")
