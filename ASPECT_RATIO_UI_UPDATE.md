# Обновление UI системы соотношений сторон

## Что исправлено

### 1. Видимость слайдера на странице генерации
**Проблема:** Блок с параметрами генерации был скрыт (`hidden` класс)  
**Решение:** Убран класс `hidden` с блока `image-params-section`

**Файл:** `templates/generate/new.html`
```html
<!-- Было -->
<div class="card p-6 mt-6 hidden" id="image-params-section">

<!-- Стало -->
<div class="card p-6 mt-6" id="image-params-section">
```

---

### 2. Дизайн клиентского селектора
**Проблема:** Сложный слайдер с иконками не соответствовал стилю сайта  
**Решение:** Переделан на простые кнопки-карточки с иконками

**Файл:** `static/js/aspect-ratio-slider.js`

**Новый дизайн:**
- Сетка кнопок-карточек (2-4 колонки)
- SVG иконки ориентации (портрет/пейзаж/квадрат)
- Активная кнопка подсвечивается фиолетовым
- Использует CSS переменные сайта: `var(--bg-card)`, `var(--text)`, `var(--primary)`
- Плавные анимации и hover эффекты

**Стили:**
```css
.aspect-ratio-btn {
    padding: 1rem;
    background: var(--bg-card);
    border: 2px solid var(--bord);
    border-radius: 12px;
    cursor: pointer;
    transition: all 0.2s;
}

.aspect-ratio-btn.active {
    border-color: var(--primary);
    background: linear-gradient(135deg, rgba(139, 92, 246, 0.1) 0%, rgba(168, 85, 247, 0.1) 100%);
    box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.1);
}
```

---

### 3. Дизайн админ-панели
**Проблема:** Непонятно какие соотношения и качества выбраны  
**Решение:** Добавлены визуальные индикаторы

**Файл:** `generate/forms_aspect_ratio.py`

**Улучшения:**

#### A. Заголовки групп соотношений
- Серый фон = ничего не выбрано
- **Зеленый фон** = есть выбранные качества
- Галочка в кружке слева
- Счетчик выбранных качеств (бейдж)
- Стрелка вниз (rotate при клике)

```python
# Зеленый заголовок если есть выбранные
has_selected = any(f"{preset.aspect_ratio}_{q[0]}" in existing_configs for q in qualities)
selected_count = sum(...)

html = f'''
<div class="{'border-green-500' if has_selected else 'border-gray-200'}">
    <div class="{'from-green-600 to-emerald-600' if has_selected else 'from-gray-600 to-gray-700'}">
        <!-- Галочка -->
        <div class="ar-ratio-toggle">
            {checkmark_svg if has_selected else ''}
        </div>
        
        <!-- Бейдж с количеством -->
        {f'<span class="badge">{selected_count}</span>' if has_selected else ''}
    </div>
</div>
'''
```

#### B. Карточки качеств (SD, HD, 4K...)
- Зеленая рамка при выборе
- Зеленая галочка справа
- Поля ширины/высоты показываются только при выборе
- Зеленая подсветка полей (focus:ring-green-500)

```python
is_checked = config_key in existing_configs

html = f'''
<div class="{'border-green-500 bg-green-50' if is_checked else 'border-gray-200'}">
    <input type="checkbox" {checked} class="w-5 h-5 text-green-600">
    <label class="{'text-green-700' if is_checked else 'text-gray-700'}">
        {quality_label}
    </label>
    
    <!-- Галочка успеха -->
    {checkmark_icon if is_checked else ''}
    
    <!-- Поля размеров (показываются при выборе) -->
    <div class="{'flex' if is_checked else 'hidden'}">
        <input data-dimension="width" class="focus:ring-green-500">
        <input data-dimension="height" class="focus:ring-green-500">
    </div>
</div>
'''
```

#### C. JavaScript для динамического обновления
```javascript
function handleQualityCheck(checkbox, aspectRatio, quality) {
    const item = checkbox.closest('.ar-quality-item');
    
    if (checkbox.checked) {
        item.classList.add('ar-quality-selected');
        // Показываем поля размеров
        dimensionsDiv.classList.remove('hidden');
        
        // Обновляем заголовок группы
        updateRatioGroupHeader(aspectRatio);
    }
}

function updateRatioGroupHeader(aspectRatio) {
    const checkedCount = group.querySelectorAll('.ar-quality-selected').length;
    
    if (checkedCount > 0) {
        header.classList.add('from-green-600', 'to-emerald-600');
        group.style.borderColor = '#22c55e';
    }
}
```

---

## Как применить изменения

### На локальной машине (Windows):
```bash
update_aspect_ratio_ui.bat
```

### На сервере (Linux):
```bash
chmod +x update_aspect_ratio_ui.sh
./update_aspect_ratio_ui.sh
```

### Вручную через Docker:
```bash
# Собрать статику
docker-compose exec web python manage.py collectstatic --noinput

# Перезапустить
docker-compose restart web
```

---

## Что проверить после обновления

### 1. Страница генерации (/generate/)
- [ ] Блок "Параметры генерации" виден сразу
- [ ] Есть секция "Соотношение сторон" с кнопками
- [ ] Кнопки показывают иконки ориентации
- [ ] При клике на кнопку она подсвечивается фиолетовым
- [ ] Селектор качества обновляется при выборе соотношения
- [ ] Поля ширина×высота автоматически заполняются

### 2. Админ-панель (ImageModelConfiguration)
- [ ] Группы без выбранных качеств - серые
- [ ] Группы с выбранными качествами - зеленые
- [ ] В заголовке группы видна галочка
- [ ] В заголовке группы видно количество выбранных
- [ ] При клике на checkbox качества:
  - Появляется зеленая рамка
  - Показываются поля размеров
  - Появляется галочка справа
- [ ] При снятии checkbox:
  - Серая рамка
  - Скрываются поля размеров
  - Убирается галочка
- [ ] Счетчик внизу показывает общее количество

---

## Технические детали

### Файлы изменены:
1. `templates/generate/new.html` - убран `hidden` класс
2. `static/js/aspect-ratio-slider.js` - полностью переписан компонент
3. `generate/forms_aspect_ratio.py` - улучшен виджет админки

### CSS переменные используемые:
- `--bg-card` - фон карточек
- `--text` - цвет текста
- `--primary` - акцентный цвет (фиолетовый)
- `--bord` - цвет границ

### Tailwind классы:
- `border-green-500` - зеленая рамка
- `bg-green-50` - светло-зеленый фон
- `from-green-600 to-emerald-600` - градиент заголовка
- `text-green-700` - зеленый текст
- `focus:ring-green-500` - зеленое кольцо фокуса

---

## Скриншоты ожидаемого результата

### Клиентская часть:
```
┌─────────────────────────────────────┐
│  Соотношение сторон                 │
├─────────────────────────────────────┤
│  ┌───┐  ┌───┐  ┌───┐  ┌───┐       │
│  │ ▭ │  │ ▯ │  │ ▭ │  │ ▭ │       │
│  │1:1│  │9:16│ │16:9│ │21:9│       │
│  └───┘  └───┘  └───┘  └───┘       │
│    ↑ активная (фиолетовая)         │
└─────────────────────────────────────┘
```

### Админ-панель:
```
┌────────────────────────────────────────┐
│ ✓ 16:9 — Стандартный        [2]      │ ← ЗЕЛЕНЫЙ
├────────────────────────────────────────┤
│  ☑ HD (1920×1080) ✓                   │ ← ЗЕЛЕНАЯ РАМКА
│    Ширина: [1920]  Высота: [1080]     │
│                                         │
│  ☑ 4K (3840×2160) ✓                   │
│    Ширина: [3840]  Высота: [2160]     │
└────────────────────────────────────────┘

┌────────────────────────────────────────┐
│   1:1 — Квадрат                        │ ← СЕРЫЙ
├────────────────────────────────────────┤
│  ☐ HD                                  │
│  ☐ 4K                                  │
└────────────────────────────────────────┘
```

---

## Обратная связь

Если что-то работает не так:

1. Проверьте консоль браузера (F12)
2. Убедитесь что статика собрана
3. Проверьте что выбрана модель с настроенными конфигурациями
4. Очистите кеш браузера (Ctrl+F5)

Логи можно посмотреть:
```bash
docker-compose logs -f web
```
