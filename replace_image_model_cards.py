"""
Скрипт для замены жестко закодированных карточек моделей изображений
на динамическую генерацию из базы данных
"""

# Найти строку с <div id="image-model-cards"
# и заменить весь блок до </div> (закрывающий тег контейнера)

template_path = "templates/generate/new.html"

# Читаем файл
with open(template_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Находим начало блока
start_marker = '<div id="image-model-cards" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">'
start_idx = content.find(start_marker)

if start_idx == -1:
    print("Не найден маркер начала блока!")
    exit(1)

# Находим конец блока (ищем закрывающий </div> после трех жестко закодированных карточек)
# Ищем после "FLUX.1.1 [pro] Ultra" закрывающий </div></div>
search_from = content.find('data-model="bfl:2@2"', start_idx)
if search_from == -1:
    print("Не найдена последняя карточка!")
    exit(1)

# Ищем два закрывающих </div> после последней карточки
first_close = content.find('</div>', search_from)
second_close = content.find('</div>', first_close + 6)
end_idx = second_close + 6  # +6 для </div>

# Новый динамический блок
new_block = '''<div id="image-model-cards" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {% for model in image_models %}
          <div class="image-model-card-wrap flex flex-col">
            {% if model.is_beta %}
            <div class="h-5 sm:h-6 mb-1 flex items-center gap-1">
              <svg class="w-3.5 h-3.5 text-purple-500" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                <path d="M10 2a8 8 0 100 16 8 8 0 000-16zm1 11H9v-2h2v2zm0-4H9V5h2v4z"/>
              </svg>
              <span class="text-[11px] sm:text-xs font-medium text-purple-600 dark:text-purple-400">Бета</span>
            </div>
            {% elif model.is_premium %}
            <div class="h-5 sm:h-6 mb-1 flex items-center gap-1">
              <svg class="w-3.5 h-3.5 text-amber-500" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"></path>
              </svg>
              <span class="text-[11px] sm:text-xs font-medium text-amber-600 dark:text-amber-400">Премиум</span>
            </div>
            {% elif forloop.first %}
            <div class="h-5 sm:h-6 mb-1 flex items-center gap-1">
              <svg class="w-3.5 h-3.5 text-emerald-500" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"></path>
              </svg>
              <span class="text-[11px] sm:text-xs font-medium text-emerald-600 dark:text-emerald-400">Рекомендуем</span>
            </div>
            {% else %}
            <div class="h-5 sm:h-6 mb-1"></div>
            {% endif %}
            <button type="button" class="image-model-card h-full w-full block group relative rounded-xl overflow-hidden border-2 border-[var(--bord)] bg-[var(--bg-card)] hover:border-primary transition-all focus:outline-none"
                    data-model="{{ model.model_id }}"
                    data-selected="{% if forloop.first %}1{% else %}0{% endif %}"
                    data-config='{{ model.optional_fields|safe }}'
                    aria-label="Выбрать модель {{ model.name }}">
              <div class="card-hero relative aspect-[16/9] overflow-hidden bg-gradient-to-br from-gray-800 to-gray-900" style="aspect-ratio:16/9; min-height:180px;">
                {% if model.image %}
                <img src="{{ model.image.url }}" alt="{{ model.name }}" class="absolute inset-0 w-full h-full object-cover" loading="{% if forloop.first %}eager{% else %}lazy{% endif %}" decoding="{% if forloop.first %}sync{% else %}async{% endif %}" {% if not forloop.first %}fetchpriority="low"{% endif %}>
                {% else %}
                <img src="/static/img/category/Пейзаж.jpg" alt="{{ model.name }}" class="absolute inset-0 w-full h-full object-cover" loading="{% if forloop.first %}eager{% else %}lazy{% endif %}" decoding="{% if forloop.first %}sync{% else %}async{% endif %}">
                {% endif %}
                <div class="card-overlay absolute inset-0 bg-gradient-to-t from-black/80 via-black/40 to-black/20 pointer-events-none"></div>
                <div class="absolute top-2 right-2 z-10">
                  <span class="px-2 py-1 rounded-full text-[10px] sm:text-xs font-semibold bg-primary/90 text-white shadow">
                    {{ model.token_cost }} TOK
                  </span>
                </div>
                <div class="absolute inset-0 card-content flex flex-col items-center justify-center px-2 sm:px-4 text-center gap-1.5 sm:gap-2">
                  <h3 class="text-white font-bold text-base sm:text-lg mb-2 drop-shadow-lg">{{ model.name }}</h3>
                  {% if model.description %}
                  <p class="text-white/90 text-xs sm:text-sm leading-snug drop-shadow-md line-clamp-2">
                    {{ model.description }}
                  </p>
                  {% endif %}
                </div>
              </div>
            </button>
          </div>
          {% empty %}
          <!-- Fallback: если нет моделей в БД, показываем стандартную -->
          <div class="image-model-card-wrap flex flex-col">
            <div class="h-5 sm:h-6 mb-1 flex items-center gap-1">
              <svg class="w-3.5 h-3.5 text-emerald-500" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"></path>
              </svg>
              <span class="text-[11px] sm:text-xs font-medium text-emerald-600 dark:text-emerald-400">Рекомендуем</span>
            </div>
            <button type="button" class="image-model-card h-full w-full block group relative rounded-xl overflow-hidden border-2 border-[var(--bord)] bg-[var(--bg-card)] hover:border-primary transition-all focus:outline-none"
                    data-model="runware:101@1" data-selected="1" aria-label="Выбрать стандартную модель">
              <div class="card-hero relative aspect-[16/9] overflow-hidden bg-gradient-to-br from-gray-800 to-gray-900" style="aspect-ratio:16/9; min-height:180px;">
                <img src="/static/img/category/Пейзаж.jpg" alt="Стандартная модель" class="absolute inset-0 w-full h-full object-cover" loading="eager" decoding="sync">
                <div class="card-overlay absolute inset-0 bg-gradient-to-t from-black/80 via-black/40 to-black/20 pointer-events-none"></div>
                <div class="absolute top-2 right-2 z-10">
                  <span class="px-2 py-1 rounded-full text-[10px] sm:text-xs font-semibold bg-primary/90 text-white shadow">
                    {% with c=price|default:TOKENS_PRICE_PER_GEN|default:10 %}{{ c }} TOK{% endwith %}
                  </span>
                </div>
                <div class="absolute inset-0 card-content flex flex-col items-center justify-center px-2 sm:px-4 text-center gap-1.5 sm:gap-2">
                  <h3 class="text-white font-bold text-base sm:text-lg mb-2 drop-shadow-lg">Стандартная</h3>
                  <p class="text-white/90 text-xs sm:text-sm leading-snug drop-shadow-md line-clamp-2">
                    Универсальная модель: стабильное качество и быстрый отклик.
                  </p>
                </div>
              </div>
            </button>
          </div>
          {% endfor %}
        </div>'''

# Заменяем блок
new_content = content[:start_idx] + new_block + content[end_idx:]

# Сохраняем
with open(template_path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print("✅ Карточки моделей изображений успешно заменены на динамическую генерацию!")
print(f"Заменено {end_idx - start_idx} символов на {len(new_block)} символов")
