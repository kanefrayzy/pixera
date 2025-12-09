"""
Скрипт для интеграции ImageFieldManager с выбором модели
"""

# Код для добавления в templates/generate/new.html
# В функцию select() после строки с localStorage

integration_code = """
        // Обновляем поля через ImageFieldManager
        if (card && card.dataset.config) {
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
"""

print("=" * 60)
print("КОД ДЛЯ ИНТЕГРАЦИИ ImageFieldManager")
print("=" * 60)
print("\nДобавить в функцию select() после строки:")
print("try{localStorage.setItem('gen.image.model',card.dataset.model)}catch(_){}")
print("\nКод для добавления:")
print(integration_code)
print("\n" + "=" * 60)
print("ПОЛНАЯ ФУНКЦИЯ select() должна выглядеть так:")
print("=" * 60)

full_function = """
function select(card){
  // Batch DOM updates
  requestAnimationFrame(()=>{
    cardsArr.forEach(c=>{
      c.dataset.selected='0';
      c.classList.remove(SELECTED);
    });
    if(card){
      hidden.value=card.dataset.model||'';
      card.dataset.selected='1';
      card.classList.add(SELECTED);
      try{localStorage.setItem('gen.image.model',card.dataset.model)}catch(_){}

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
    }
  });
}
"""

print(full_function)
