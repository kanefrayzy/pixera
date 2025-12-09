"""
Полная реализация множественной генерации видео
- Добавляет UI для выбора количества видео
- Обновляет расчёт цены
- Обновляет backend для обработки количества
"""

import os
import sys

# Добавляем путь к Django проекту
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_gallery.settings')

import django
django.setup()

def main():
    print("="*60)
    print("РЕАЛИЗАЦИЯ МНОЖЕСТВЕННОЙ ГЕНЕРАЦИИ ВИДЕО")
    print("="*60)

    # Шаг 1: Обновляем video-field-manager.js для поддержки количества
    print("\n📝 Шаг 1: Обновляем video-field-manager.js...")

    js_file = 'static/js/video-field-manager.js'

    if not os.path.exists(js_file):
        print(f"❌ Файл {js_file} не найден!")
        return False

    with open(js_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Проверяем, не добавлено ли уже
    if 'updateVideoQuantity' in content:
        print("✅ Поддержка количества уже добавлена в video-field-manager.js")
    else:
        # Находим место для вставки (после updateVideoPrice)
        insert_marker = '// Update price display'
        if insert_marker in content:
            # Добавляем функцию для обновления количества
            quantity_code = '''
    // Update video quantity based on model support
    updateVideoQuantity(modelData) {
        const quantityContainer = document.getElementById('video-quantity-container');
        const quantityInput = document.getElementById('video-quantity');
        const quantityValue = document.getElementById('video-quantity-value');

        if (!quantityContainer || !quantityInput) return;

        if (modelData.supports_multiple_videos && modelData.multiple_videos_range) {
            const range = modelData.multiple_videos_range;
            quantityContainer.style.display = 'block';
            quantityInput.min = range.min;
            quantityInput.max = range.max;
            quantityInput.value = range.default;
            if (quantityValue) {
                quantityValue.textContent = range.default;
            }

            // Add event listener for quantity change
            quantityInput.removeEventListener('input', this.handleQuantityChange);
            quantityInput.addEventListener('input', this.handleQuantityChange.bind(this));
        } else {
            quantityContainer.style.display = 'none';
            quantityInput.value = 1;
        }

        // Update price after quantity change
        this.updateVideoPrice();
    }

    // Handle quantity change
    handleQuantityChange(event) {
        const quantityValue = document.getElementById('video-quantity-value');
        if (quantityValue) {
            quantityValue.textContent = event.target.value;
        }
        this.updateVideoPrice();
    }

'''
            content = content.replace(insert_marker, quantity_code + '\n    ' + insert_marker)

            # Обновляем updateVideoPrice для учёта количества
            old_price_calc = 'const totalCost = this.currentModel.token_cost;'
            new_price_calc = '''const quantity = parseInt(document.getElementById('video-quantity')?.value || 1);
        const totalCost = this.currentModel.token_cost * quantity;'''
            content = content.replace(old_price_calc, new_price_calc)

            # Добавляем вызов updateVideoQuantity в updateFieldsForModel
            old_update = 'this.updateVideoPrice();'
            new_update = '''this.updateVideoQuantity(modelData);
        this.updateVideoPrice();'''
            content = content.replace(old_update, new_update)

            with open(js_file, 'w', encoding='utf-8') as f:
                f.write(content)

            print("✅ Добавлена поддержка количества в video-field-manager.js")

    # Шаг 2: Обновляем video-generation.js для отправки количества
    print("\n📝 Шаг 2: Обновляем video-generation.js...")

    video_gen_file = 'static/js/video-generation.js'

    if os.path.exists(video_gen_file):
        with open(video_gen_file, 'r', encoding='utf-8') as f:
            gen_content = f.read()

        if 'number_videos' not in gen_content:
            # Добавляем отправку количества
            old_formdata = "formData.append('video_model_id', videoModelId);"
            new_formdata = """formData.append('video_model_id', videoModelId);

        // Add number of videos if supported
        const quantityInput = document.getElementById('video-quantity');
        if (quantityInput && quantityInput.value) {
            formData.append('number_videos', quantityInput.value);
        }"""
            gen_content = gen_content.replace(old_formdata, new_formdata)

            with open(video_gen_file, 'w', encoding='utf-8') as f:
                f.write(gen_content)

            print("✅ Добавлена отправка количества в video-generation.js")
        else:
            print("✅ Отправка количества уже настроена в video-generation.js")

    # Шаг 3: Добавляем HTML для выбора количества
    print("\n📝 Шаг 3: Создаём HTML компонент для количества...")

    html_component = '''<!-- Video Quantity Selector -->
<div id="video-quantity-container" class="form-group" style="display: none;">
    <label for="video-quantity">
        <i class="fas fa-layer-group"></i>
        Количество видео
    </label>
    <div class="quantity-selector">
        <input
            type="range"
            id="video-quantity"
            name="number_videos"
            min="1"
            max="4"
            value="1"
            class="form-range"
        >
        <div class="quantity-display">
            <span id="video-quantity-value">1</span>
            <span class="quantity-label">видео</span>
        </div>
    </div>
    <small class="form-text text-muted">
        Цена умножается на количество видео
    </small>
</div>'''

    component_file = 'VIDEO_QUANTITY_COMPONENT.html'
    with open(component_file, 'w', encoding='utf-8') as f:
        f.write(html_component)

    print(f"✅ Создан компонент: {component_file}")
    print("   Добавьте его в templates/generate/video_form.html после выбора модели")

    # Шаг 4: Создаём CSS для компонента
    print("\n📝 Шаг 4: Создаём CSS стили...")

    css_styles = '''/* Video Quantity Selector Styles */
#video-quantity-container {
    margin: 20px 0;
    padding: 15px;
    background: #f8f9fa;
    border-radius: 8px;
}

#video-quantity-container label {
    display: block;
    margin-bottom: 10px;
    font-weight: 600;
    color: #333;
}

#video-quantity-container label i {
    margin-right: 8px;
    color: #007bff;
}

.quantity-selector {
    display: flex;
    align-items: center;
    gap: 15px;
}

.quantity-selector .form-range {
    flex: 1;
    height: 6px;
    background: #dee2e6;
    border-radius: 3px;
    outline: none;
}

.quantity-selector .form-range::-webkit-slider-thumb {
    width: 20px;
    height: 20px;
    background: #007bff;
    border-radius: 50%;
    cursor: pointer;
}

.quantity-selector .form-range::-moz-range-thumb {
    width: 20px;
    height: 20px;
    background: #007bff;
    border-radius: 50%;
    cursor: pointer;
    border: none;
}

.quantity-display {
    display: flex;
    align-items: center;
    gap: 5px;
    min-width: 80px;
    padding: 8px 15px;
    background: white;
    border: 2px solid #007bff;
    border-radius: 6px;
    font-weight: 600;
}

#video-quantity-value {
    font-size: 1.2em;
    color: #007bff;
}

.quantity-label {
    color: #666;
    font-size: 0.9em;
}'''

    css_file = 'VIDEO_QUANTITY_STYLES.css'
    with open(css_file, 'w', encoding='utf-8') as f:
        f.write(css_styles)

    print(f"✅ Созданы стили: {css_file}")
    print("   Добавьте их в static/css/video-generation-fix.css")

    print("\n" + "="*60)
    print("✅ РЕАЛИЗАЦИЯ ЗАВЕРШЕНА!")
    print("="*60)

    print("\n📋 ЧТО НУЖНО СДЕЛАТЬ ВРУЧНУЮ:")
    print("\n1. Добавьте HTML компонент из VIDEO_QUANTITY_COMPONENT.html")
    print("   в templates/generate/video_form.html после блока выбора модели")

    print("\n2. Добавьте CSS стили из VIDEO_QUANTITY_STYLES.css")
    print("   в static/css/video-generation-fix.css")

    print("\n3. В админке создайте/обновите модель видео:")
    print("   - Откройте http://127.0.0.1:8000/generate/admin/video-models/create")
    print("   - Поставьте галочку 'Поддерживает множественную генерацию'")
    print("   - Установите минимум, максимум и значение по умолчанию")

    print("\n4. Перезапустите сервер Django:")
    print("   python manage.py runserver")

    print("\n" + "="*60)

    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
