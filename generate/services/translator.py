"""
Сервис перевода промтов с использованием DeepL API
"""
import logging
import requests
from django.conf import settings
from typing import Optional

logger = logging.getLogger(__name__)


class DeepLTranslator:
    """Класс для перевода текста с использованием DeepL API"""
    
    def __init__(self):
        self.api_key = getattr(settings, 'DEEPL_API_KEY', '')
        self.api_url = "https://api-free.deepl.com/v2/translate"  # Free API URL
        self.pro_api_url = "https://api.deepl.com/v2/translate"  # Pro API URL
        
    def is_english(self, text: str) -> bool:
        """Проверяет, является ли текст английским языком"""
        if not text:
            return True
            
        # Список распространенных не-английских слов и символов
        non_english_indicators = [
            # Французский
            'é', 'è', 'ê', 'à', 'ç', 'ù', 'û', 'î', 'ï', 'â', 'ô', 'ë', 'ü', 'ä', 'ö',
            'le', 'la', 'les', 'de', 'du', 'des', 'et', 'est', 'dans', 'pour', 'avec',
            'beau', 'belle', 'mer', 'soleil', 'coucher', 'sur',
            # Испанский
            'ñ', 'á', 'í', 'ó', 'ú', 'ü', '¿', '¡',
            'el', 'la', 'los', 'las', 'de', 'del', 'y', 'en', 'por', 'con', 'para',
            'hermoso', 'hermosa', 'atardecer', 'mar',
            # Итальянский
            'gli', 'del', 'della', 'sul', 'bel', 'bella',
            'tramonto', 'mare',
            # Немецкий
            'ß', 'ä', 'ö', 'ü',
            'der', 'die', 'das', 'und', 'in', 'an', 'auf', 'mit',
            'schön', 'sonnenuntergang', 'meer',
            # Португальский
            'ão', 'õ', 'á', 'â', 'ê', 'ô',
            'o', 'a', 'os', 'as', 'de', 'do', 'da', 'dos', 'das', 'em',
            'belo', 'pôr', 'sol',
            # Голландский
            'de', 'het', 'een', 'van', 'in', 'op', 'met', 'voor',
            'mooie', 'zonsondergang', 'boven', 'zee',
            # Русский
            'а', 'б', 'в', 'г', 'д', 'е', 'ё', 'ж', 'з', 'и', 'й', 'к', 'л', 'м', 'н', 'о', 'п', 'р', 'с', 'т', 'у', 'ф', 'х', 'ц', 'ч', 'ш', 'щ', 'ъ', 'ы', 'ь', 'э', 'ю', 'я',
            'красивый', 'закат', 'над', 'морем',
        ]
        
        text_lower = text.lower()
        
        # Проверяем на наличие не-английских символов
        for indicator in non_english_indicators:
            if indicator in text_lower:
                return False
        
        # Проверяем на наличие символов вне базового английского алфавита
        allowed_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .,!?-:;()[]{}"\'')
        text_chars = set(text[:100])
        non_english_chars = text_chars - allowed_chars
        if non_english_chars:
            return False
            
        # Если дошли сюда, считаем что это английский
        return True
    
    def translate_to_english(self, text: str) -> Optional[str]:
        """
        Переводит текст на английский язык
        Возвращает None в случае ошибки
        """
        logger.info(f"Начинаем перевод текста: '{text[:50]}...'")
        
        if not text or not text.strip():
            logger.warning("Пустой текст для перевода")
            return text
            
        # Если текст уже на английском, возвращаем как есть
        if self.is_english(text):
            logger.info("Текст уже на английском, перевод не требуется")
            return text
            
        logger.info(f"API ключ настроен: {'Да' if self.api_key else 'Нет'}")
        if not self.api_key:
            logger.warning("DeepL API key не настроен")
            return text
            
        try:
            # Определяем URL API в зависимости от ключа
            api_url = self.pro_api_url if self.api_key.startswith(':fx') else self.api_url
            logger.info(f"Используем API URL: {api_url}")
            
            payload = {
                'auth_key': self.api_key,
                'text': text,
                'target_lang': 'EN'
            }
            
            logger.info(f"Отправляем запрос к DeepL API...")
            response = requests.post(api_url, data=payload, timeout=10)
            logger.info(f"Статус ответа: {response.status_code}")
            
            response.raise_for_status()
            
            result = response.json()
            logger.debug(f"Ответ API: {result}")
            
            if 'translations' in result and len(result['translations']) > 0:
                translated_text = result['translations'][0]['text']
                logger.info(f"Текст переведен: '{text[:50]}...' -> '{translated_text[:50]}...' ")
                return translated_text
            else:
                logger.error(f"Некорректный ответ от DeepL API: {result}")
                return text
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка запроса к DeepL API: {e}")
            return text
        except Exception as e:
            logger.error(f"Ошибка перевода текста: {e}")
            return text
    
    def translate_prompt(self, prompt: str) -> str:
        """
        Переводит промпт на английский язык
        Всегда возвращает строку (в случае ошибки возвращает оригинальный текст)
        """
        if not prompt:
            return prompt
            
        translated = self.translate_to_english(prompt)
        return translated if translated is not None else prompt


# Глобальный экземпляр переводчика
_translator_instance = None


def get_translator() -> DeepLTranslator:
    """Возвращает экземпляр переводчика (singleton)"""
    global _translator_instance
    if _translator_instance is None:
        _translator_instance = DeepLTranslator()
    return _translator_instance


def translate_prompt_if_needed(prompt: str) -> str:
    """
    Переводит промпт на английский если нужно
    Удобная функция для использования в коде
    """
    translator = get_translator()
    return translator.translate_prompt(prompt)
